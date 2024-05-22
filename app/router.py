from fastapi import APIRouter, Body

from app.controllers.jeju_onul_controller import JejuOnulController
from app.models.vroouty import VRooutyResponse
from app.schemas.request import JejuRequest


tag: str = "v1"
router = APIRouter(prefix=f"/{tag}", tags=[tag])


@router.post(path="/", description="Cut Off 이전 경로")
async def jeju_onul_before_wave(request: JejuRequest = Body()):
    controller = JejuOnulController(request=request)
    responses: VRooutyResponse = await controller.process_wave1()
    test = await controller.make_before_wave_response(responses=responses)
    return test
