from pydantic import BaseModel, Field, RootModel

from app.constants.work import StepType, TaskType
from app.models.coordinate import Coordinate
from app.schemas.common import CustomAttribute


# VRoouty Request Param Schema
class Job(BaseModel):
    id: int = Field()
    location: Coordinate = Field()
    setup: int = Field()
    service: int = Field()


class Shipment(BaseModel):
    pickup: Job = Field()
    delivery: Job = Field()


class Vehicle(BaseModel):
    id: int | None = Field(default=0)
    profile: str | None = Field(default=None)
    start: Coordinate = Field()


class RequestParam(BaseModel):
    jobs: list[Job] = Field()
    shipments: list[Shipment] = Field()
    vehicles: list[Vehicle] = Field()
    distribute_options: dict = Field()


# VRoouty Response Param Schema
class CommonFields(BaseModel):
    service: int = Field()
    duration: int = Field()
    waiting_time: int = Field()
    violations: list = Field()
    distance: int = Field()


class Steps(CommonFields, CustomAttribute):
    id: int = Field()
    type: StepType = Field()
    arrival: int = Field()
    location: Coordinate = Field()
    location_index: int = Field()


class Routes(CommonFields, CustomAttribute):
    vehicle: int = Field()
    steps: list[Steps] = Field()
    cost: int = Field()
    setup: int = Field()
    priority: int = Field()
    geometry: str = Field()


class Unassigned(CustomAttribute):
    id: int = Field()
    type: TaskType = Field()
    description: str = Field()
    location: Coordinate = Field()
    location_index: int = Field()


class ComputingTimes(CustomAttribute):
    loading: int = Field()
    solving: int = Field()
    routing: int = Field()


class Summary(CommonFields, CustomAttribute):
    routes: int = Field()
    unassigned: int = Field()
    setup: int = Field()
    cost: int = Field()
    priority: int = Field()
    computing_times: ComputingTimes = Field()


class VRooutyResponse(CustomAttribute):
    code: int = Field()
    summary: Summary = Field()
    unassigned: list[Unassigned] = Field()
    routes: list[Routes] = Field()


class VRooutyResponses(RootModel):
    root: dict[str, VRooutyResponse]
