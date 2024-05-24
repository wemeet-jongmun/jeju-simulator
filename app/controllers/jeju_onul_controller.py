import asyncio
from collections import defaultdict
from datetime import timedelta
from fastapi import HTTPException
from shapely.geometry import Polygon
from app.constants.vehicles import RELAY_VEHICLE_TIME
from app.constants.work import StepType, TaskType, WorkStatus
from app.models.task import Task, VehicleSwaps, VehicleTasks
from app.models.vroouty import (
    Job,
    RequestParam,
    Routes,
    Shipment,
    VRooutyResponse,
    VRooutyResponses,
    Vehicle,
)
from app.schemas.request import JejuRequest, Work
from app.schemas.response import AfterResponse, BeforeResponse
from app.utils.identity import IdHandler
from app.utils.polygon import assign_group_id
from app.utils.aiohttp import VRooutyRequest


class JejuOnulController:

    def __init__(self, request: JejuRequest) -> None:
        self.id_handler = IdHandler()
        self.request: JejuRequest = request

        # 권역에 대한 Dict
        group_polygons = {p.id: Polygon(p.polygon) for p in request.boundaries}

        pickup_location_cnt = defaultdict(int)
        delivery_location_cnt = defaultdict(int)

        # 수거 및 배송지에 대한 권역 지정
        for work in request.works:
            if group_id := assign_group_id(
                location=work.pickup.location, polygons=group_polygons
            ):
                work.pickup.group_id = group_id
            if group_id := assign_group_id(
                location=work.delivery.location, polygons=group_polygons
            ):
                work.delivery.group_id = group_id

            pickup_location_cnt[
                (work.pickup.location.longitude, work.pickup.location.latitude)
            ] += 1
            delivery_location_cnt[
                (work.delivery.location.longitude, work.delivery.location.latitude)
            ] += 1

        pickup_duplicated_locations = [
            location for location, count in pickup_location_cnt.items() if count >= 2
        ]
        delivery_duplicated_locations = [
            location for location, count in delivery_location_cnt.items() if count >= 2
        ]

        # 중복 수거 및 배송지에 대한 시간 할당
        for work in request.works:
            work.pickup.setup_time = (
                timedelta(seconds=300)
                if tuple(work.pickup.location) in pickup_duplicated_locations
                else timedelta(seconds=180)
            )
            work.pickup.service_time = timedelta(seconds=10)
            work.delivery.setup_time = (
                timedelta(seconds=300)
                if tuple(work.delivery.location) in delivery_duplicated_locations
                else timedelta(seconds=180)
            )
            work.delivery.service_time = timedelta(seconds=10)

    # Support
    def mapped_task_type(self, _type: str) -> TaskType:
        if _type in ["pickup", "shipment_pickup"]:
            return TaskType.PICKUP
        elif _type in ["delivery", "shipment_delivery"]:
            return TaskType.DELIVERY
        else:
            return TaskType(_type)

    async def before_task_delivery_done(self, vehicle_tasks: VehicleTasks) -> None:
        doned_list = []
        for vehicle_task in vehicle_tasks:
            for task in vehicle_task.tasks:
                if task.type == TaskType.DELIVERY:
                    doned_list.append(task.work_id)

        for work in self.request.works:
            if work.id in doned_list:
                work.status.type = WorkStatus.DONE

    async def process_reallocation(
        self, routes: Routes, step_list: list[int], max_assemble_time: int
    ):
        _jobs = []
        _vehicles = []

        # 재배치를 위한 작업 목록 생성
        for work in self.request.works:
            if (
                work.status.type == WorkStatus.SHIPPED
                and self.id_handler.get_index(id=routes.vehicle)[1]
                == work.status.vehicle_id
            ):
                _jobs.append(
                    Job(
                        id=self.id_handler.set("delivery", work.id),
                        location=work.delivery.location,
                        setup=work.delivery.get_setup_time,
                        service=work.delivery.get_service_time,
                    )
                )
            elif (
                work.status.type == WorkStatus.WAITING
                and self.id_handler.set("pickup", work.id) in step_list
            ):
                _jobs.append(
                    Job(
                        id=self.id_handler.set("pickup", work.id),
                        location=work.pickup.location,
                        setup=work.pickup.get_setup_time,
                        service=work.pickup.get_service_time,
                        priority=1,
                    )
                )

        # 재배치를 위한 차량 목록 생성
        for vehicle in self.request.vehicles:
            if vehicle.id == self.id_handler.get_index(id=routes.vehicle)[1]:
                _vehicles.append(
                    Vehicle(
                        id=self.id_handler.set("vehicle", vehicle.id),
                        profile=vehicle.profile,
                        start=vehicle.current_location,
                        end=next(iter(self.request.assemblies)).location,
                    )
                )
                break

        # VRoouty 요청 파라미터 생성 및 요청
        vroouty_request_param = RequestParam(
            jobs=_jobs,
            shipments=[],
            vehicles=_vehicles,
            distribute_options={
                "max_vehicle_work_time": max_assemble_time,
                "custom_matrix": {"enabled": True},
            },
        )
        response = await VRooutyRequest(param=vroouty_request_param)

        if not response:
            raise HTTPException(500)

        return response

    def create_vehicle_tasks(self, route: Routes):
        tasks = []

        # 경로의 각 단계를 처리하여 작업 목록 생성
        for step in route.steps:
            if step.type in [TaskType.JOB, TaskType.PICKUP, TaskType.DELIVERY]:
                _type, work_id = self.id_handler.get_index(id=step.id)
                if _type in [
                    TaskType.PICKUP,
                    TaskType.SHIPMENT_PICKUP,
                    TaskType.DELIVERY,
                    TaskType.SHIPMENT_DELIVERY,
                ]:
                    tasks.append(
                        Task(
                            work_id=work_id,
                            type=TaskType(_type),
                            eta=step.arrival,
                            duration=step.duration,
                            distance=step.distance,
                            setup_time=step.setup,
                            service_time=step.service,
                            assembly_id=None,
                            location=step.location,
                        )
                    )
            elif step.type == TaskType.END:
                tasks.append(
                    Task(
                        work_id=None,
                        type=TaskType.ARRIVAL,
                        eta=step.arrival,
                        duration=step.duration,
                        setup_time=step.setup,
                        service_time=step.service,
                        assembly_id=next(iter(self.request.assemblies)).id,
                        location=step.location,
                    )
                )
        # 작업 목록을 VehicleTasks 객체에 추가
        _, vehicle_id = self.id_handler.get_index(id=route.vehicle)
        return [VehicleTasks(vehicle_id=vehicle_id, tasks=tasks)]

    # Waves
    async def process_wave_before_cut_off(self) -> VRooutyResponse:
        responses = {}

        # 배송 기사에 대한 주문건 Mapping 변수 초기화
        vehicle_to_works: dict[str, list[Work]] = {
            vehicle.id: [] for vehicle in self.request.vehicles
        }

        # 권역에 대한 배송기사 Mapping 변수 초기화
        group_to_vehicles: dict[str, str] = {
            group_id: vehicle.id
            for vehicle in self.request.vehicles
            for group_id in vehicle.include
        }

        # 배송 기사의 권역에 따라 주문건 배정
        for work in self.request.works:
            if work.exception:
                vehicle_to_works[work.fix_vehicle_id].append(work)
            else:
                _vehicle_id = group_to_vehicles[work.pickup.group_id]
                vehicle_to_works[_vehicle_id].append(work)

        # Async 처리 요청을 위한 리스트
        tasks = []

        # VRoouty Call을 위한 Request 생성
        for vehicle in self.request.vehicles:
            _jobs: list[Job] = []
            _shipments: list[Shipment] = []
            _vehicles: list[Vehicle] = []

            # Job 데이터 생성
            _jobs.extend(
                [
                    Job(
                        id=self.id_handler.set("pickup", work.id),
                        location=work.pickup.location,
                        setup=work.pickup.get_setup_time,
                        service=work.pickup.get_service_time,
                    )
                    for work in vehicle_to_works[vehicle.id]
                    if work.status.type == TaskType.WAITING
                ]
            )

            # Vehicle 데이터 생성
            _vehicles.append(
                Vehicle(
                    id=self.id_handler.set("vehicle", vehicle.id),
                    profile=vehicle.profile,
                    start=vehicle.current_location,
                )
            )

            # Job이 없다면 Process 중지
            if not _jobs:
                continue

            # VRoouty Call을 위한 Request Parameter 생성
            vroouty_request_param = RequestParam(
                jobs=_jobs,
                shipments=_shipments,
                vehicles=_vehicles,
                distribute_options={"custom_matrix": {"enabled": True}},
            )
            tasks.append((vehicle.id, VRooutyRequest(param=vroouty_request_param)))

        results = await asyncio.gather(*[task[1] for task in tasks])

        # 요청 결과에 대한 처리
        for vehicle_id, result in zip([task[0] for task in tasks], results):
            if not result:
                continue

            # 각 차량의 배차 결과가 30분 이내에 완료될 시 부권역과 Delivery 추가 후 재배차
            if RELAY_VEHICLE_TIME > next(
                step.arrival
                for route in result.routes
                for step in route.steps
                if step.type == StepType.END
            ):
                _jobs.clear()
                for work in vehicle_to_works[vehicle_id]:
                    if work.status.type == WorkStatus.WAITING:
                        if work.pickup.group_id in vehicle.exclude:
                            _jobs.append(
                                Job(
                                    id=self.id_handler.set("pickup", work.id),
                                    location=work.pickup.location,
                                    setup=work.pickup.get_setup_time,
                                    service=work.pickup.get_service_time,
                                )
                            )
                        if (
                            work.pickup.group_id in vehicle.include
                            and work.delivery.group_id in vehicle.include
                        ):
                            _shipments.append(
                                Shipment(
                                    pickup=Job(
                                        id=self.id_handler.set("pickup", work.id),
                                        location=work.pickup.location,
                                        setup=work.pickup.get_setup_time,
                                        service=work.pickup.get_service_time,
                                    ),
                                    delivery=Job(
                                        id=self.id_handler.set("delivery", work.id),
                                        location=work.delivery.location,
                                        setup=work.delivery.get_setup_time,
                                        service=work.delivery.get_service_time,
                                    ),
                                )
                            )
                            continue
                        _jobs.append(
                            Job(
                                id=self.id_handler.set("pickup", work.id),
                                location=work.pickup.location,
                                setup=work.pickup.get_setup_time,
                                service=work.pickup.get_service_time,
                            )
                        )
                    elif (
                        work.status.type == WorkStatus.SHIPPED
                        and work.delivery.group_id in vehicle.include
                    ):
                        _jobs.append(
                            Job(
                                id=self.id_handler.set("delivery", work.id),
                                location=work.delivery.location,
                                setup=work.delivery.get_setup_time,
                                service=work.delivery.get_service_time,
                            )
                        )
                    vroouty_request_param = RequestParam(
                        jobs=_jobs,
                        shipments=_shipments,
                        vehicles=_vehicles,
                        distribute_options={"custom_matrix": {"enabled": True}},
                    )
                    response = await VRooutyRequest(param=vroouty_request_param)

                if not response:
                    raise HTTPException(500)

            responses[vehicle_id] = result
        return VRooutyResponses(root=responses)

    async def process_wave_after_cut_off(
        self,
        job_status_condition: callable,
        vehicle_start_location: callable,
        prefix: str,
    ) -> VRooutyResponse:
        # Job 데이터 생성
        _jobs = [
            Job(
                id=self.id_handler.set(prefix, work.id),
                location=work.pickup.location,
                setup=work.pickup.get_setup_time,
                service=work.pickup.get_service_time,
            )
            for work in self.request.works
            if job_status_condition(work.status.type)
        ]

        # Vehicle 데이터 생성
        _vehicles = [
            Vehicle(
                id=self.id_handler.set("vehicle", vehicle.id),
                profile=vehicle.profile,
                start=vehicle_start_location(vehicle),
            )
            for vehicle in self.request.vehicles
        ]

        # VRoouty 요청 파라미터 생성
        vroouty_request_param = RequestParam(
            jobs=_jobs,
            shipments=[],
            vehicles=_vehicles,
            distribute_options={
                "equalize_work_time": {"enabled": True},
                "custom_matrix": {"enabled": True},
            },
        )
        response = await VRooutyRequest(param=vroouty_request_param)

        if not response:
            raise HTTPException(500)

        return response

        # Job 데이터 생성
        _jobs = [
            Job(
                id=self.id_handler.set("delivery", work.id),
                location=work.pickup.location,
                setup=work.pickup.get_setup_time,
                service=work.pickup.get_service_time,
            )
            for work in self.request.works
            if work.status.type != WorkStatus.DONE
        ]

        # Vehicle 데이터 생성
        assembly_location = next(iter(self.request.assemblies)).location
        _vehicles = [
            Vehicle(
                id=self.id_handler.set("vehicle", vehicle.id),
                profile=vehicle.profile,
                start=assembly_location,
            )
            for vehicle in self.request.vehicles
        ]

        # VRoouty 요청 파라미터 생성
        vroouty_request_param = RequestParam(
            jobs=_jobs,
            vehicles=_vehicles,
            distribute_options={
                "equalize_work_time": {"enabled": True},
                "custom_matrix": {"enabled": True},
            },
        )
        response = await VRooutyRequest(param=vroouty_request_param)

        if not response:
            raise HTTPException(500)

        return response

    # Response Processing
    async def make_before_wave_response(
        self, responses: VRooutyResponse
    ) -> BeforeResponse:
        tasks: list[VehicleTasks] = []
        unassigned: list = []

        vehicle_dict = {str(vehicle.id): vehicle for vehicle in self.request.vehicles}
        assemblies_dict = {
            tuple(assembly.location): assembly for assembly in self.request.assemblies
        }

        for vehicle_id, vehicle in vehicle_dict.items():
            _tasks: list[Task] = []

            response: Routes = responses.root.get(vehicle_id, None)

            if response:
                for route in response.routes:
                    for step in route.steps:
                        if step.type in [
                            TaskType.JOB,
                            TaskType.PICKUP,
                            TaskType.DELIVERY,
                        ]:
                            _type, work_id = self.id_handler.get_index(id=step.id)
                            if _type in [
                                TaskType.PICKUP,
                                TaskType.SHIPMENT_PICKUP,
                                TaskType.DELIVERY,
                                TaskType.SHIPMENT_DELIVERY,
                            ]:
                                _tasks.append(
                                    Task(
                                        work_id=work_id,
                                        type=TaskType(_type),
                                        eta=step.arrival,
                                        duration=step.duration,
                                        distance=step.distance,
                                        setup_time=step.setup,
                                        service_time=step.service,
                                        assembly_id=None,
                                        location=step.location,
                                    )
                                )
                        elif step.type == TaskType.END:
                            if assemblies_dict.get(tuple(step.location), None):
                                _tasks.append(
                                    Task(
                                        work_id=None,
                                        type=TaskType.ARRIVAL,
                                        eta=step.arrival,
                                        duration=step.duration,
                                        setup_time=step.setup,
                                        service_time=step.service,
                                        assembly_id=None,
                                        location=step.location,
                                    )
                                )
            tasks.append(
                VehicleTasks(
                    vehicle_id=vehicle.id,
                    tasks=_tasks,
                )
            )

        return BeforeResponse(
            vehicle_tasks=tasks,
            unassigned=unassigned,
        )

    async def make_pickup_response(
        self, response: VRooutyResponse
    ) -> list[VehicleTasks]:
        vehicle_tasks: list[VehicleTasks] = []

        # 각 경로의 마지막 단계 도착 시간을 수집
        assemble_times = [route.steps[-1].arrival for route in response.routes]
        max_assemble_time = max(assemble_times)

        for route in response.routes:
            # Job의 step ID를 수집
            step_list = [step.id for step in route.steps if step.type == StepType.JOB]

            # 마지막 step 도착 시간이 최대 집결 시간보다 작으면 재배차
            if route.steps[-1].arrival < max_assemble_time:
                reallocated_response = await self.process_reallocation(
                    routes=route,
                    step_list=step_list,
                    max_assemble_time=max_assemble_time,
                )
                _vehicle_tasks = []
                for reallocated_route in reallocated_response.routes:
                    _vehicle_tasks.extend(
                        self.create_vehicle_tasks(route=reallocated_route)
                    )
            else:
                _vehicle_tasks = self.create_vehicle_tasks(route=route)

            vehicle_tasks.extend(_vehicle_tasks)

        # 작업 완료 후 추가 처리 수행
        await self.before_task_delivery_done(vehicle_tasks=vehicle_tasks)
        return vehicle_tasks

    async def make_delivery_response(
        self, response: VRooutyResponse
    ) -> list[VehicleTasks]:
        _tasks = []

        # 각 경로의 작업 목록 생성
        for route in response.routes:
            tasks = self.create_vehicle_tasks(route=route)
            _tasks.extend(tasks)

        return _tasks

    async def make_combine_after_response(
        self, before_tasks: list[VehicleTasks], after_tasks: list[VehicleTasks]
    ) -> AfterResponse:
        swaps: list[VehicleSwaps] = []
        end_time = []

        for vehicle in self.request.vehicles:
            shipped_tasks = []
            need_tasks = []

            for vehicle_tasks in before_tasks:
                if vehicle_tasks.vehicle_id == vehicle.id:
                    for task in vehicle_tasks.tasks:
                        if task.work_id:
                            shipped_tasks.append(task.work_id)
                        if task.type == TaskType.ARRIVAL:
                            end_time.append(task.eta)

            for work in self.request.works:
                if work.status.type == WorkStatus.SHIPPED:
                    if work.status.vehicle_id == vehicle.id:
                        shipped_tasks.append(work.id)

            for deliver_tasks in after_tasks:
                if deliver_tasks.vehicle_id == vehicle.id:
                    for task in deliver_tasks.tasks:
                        if task.work_id:
                            need_tasks.append(task.work_id)

            up = list(set(need_tasks) - set(shipped_tasks))
            down = list(set(shipped_tasks) - set(need_tasks))

            swaps.append(
                VehicleSwaps(
                    vehicle_id=vehicle.id,
                    assembly_id=next(iter(self.request.assemblies)).id,
                    stop_over_time=0,
                    up=up,
                    down=down,
                )
            )

        for swap in swaps:
            swap.stop_over_time = max(end_time)

        return AfterResponse(
            before_tasks=before_tasks, after_tasks=after_tasks, swaps=swaps
        )
