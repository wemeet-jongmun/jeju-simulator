from fastapi import APIRouter, Body, Request

from app.constants.work import WorkStatus
from app.controllers.jeju_onul_controller import JejuOnulController
from app.models.vroouty import VRooutyResponse
from app.schemas.request import JejuRequest
from app.schemas.response import AfterResponse, BeforeResponse


tag: str = "v1"
router = APIRouter(prefix=f"/{tag}", tags=[tag])


@router.post(
    path="/before",
    description="Cut Off 이전 경로",
    response_model=BeforeResponse,
    response_model_exclude_none=True,
)
async def jeju_onul_before_wave(request: JejuRequest = Body()) -> BeforeResponse:
    controller = JejuOnulController(request=request)
    responses: VRooutyResponse = await controller.process_wave_before_cut_off()
    return await controller.make_before_wave_response(responses=responses)


@router.post(
    path="/after",
    description="Cut Off 이후 경로",
    response_model=AfterResponse,
    response_model_exclude_none=True,
)
async def jeju_onul_after_wave(request: JejuRequest = Body()) -> AfterResponse:
    controller = JejuOnulController(request=request)
    to_pickup_result = await controller.process_wave_after_cut_off(
        job_status_condition=lambda status: status == WorkStatus.WAITING.value,
        vehicle_start_location=lambda vehicle: vehicle.current_location,
        prefix="pickup",
    )
    assembly_location = next(iter(controller.request.assemblies)).location
    to_delivery_result = await controller.process_wave_after_cut_off(
        job_status_condition=lambda status: status != WorkStatus.DONE.value,
        vehicle_start_location=lambda vehicle: assembly_location,
        prefix="delivery",
    )
    pickup_response = await controller.make_pickup_response(response=to_pickup_result)
    delivery_response = await controller.make_delivery_response(
        response=to_delivery_result
    )
    return await controller.make_combine_after_response(
        before_tasks=pickup_response, after_tasks=delivery_response
    )
