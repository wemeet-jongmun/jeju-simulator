import asyncio
from collections import defaultdict
from datetime import timedelta
from fastapi import HTTPException
from shapely.geometry import Polygon
from app.constants.vehicles import RELAY_VEHICLE_TIME
from app.constants.work import StepType, TaskType, WorkStatus
from app.models.task import Task, VehicleTasks
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
from app.schemas.response import BeforeResponse
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

    # Waves
    async def process_wave1(self) -> VRooutyResponse:
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

            # 각차량의 배차 결과가 30분 이내에 완료될 시 부권역과 Delivery 추가 후 재배차
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
                            _type, work_id = self.id_handler.get_from_index(
                                index=step.id
                            )
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
                                        serice_time=step.service,
                                        assembly_id=None,
                                        location=step.location,
                                    )
                                )
                        elif step.type == TaskType.END:
                            if assembly := assemblies_dict.get(
                                tuple(step.location), None
                            ):
                                _tasks.append(
                                    Task(
                                        work_id=None,
                                        type=TaskType.ARRIVAL,
                                        eta=step.arrival,
                                        duration=step.duration,
                                        setup_time=step.setup,
                                        serice_time=step.service,
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
