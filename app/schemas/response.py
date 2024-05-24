from pydantic import BaseModel, Field, NonNegativeInt

from app.models.task import VehicleSwaps, VehicleTasks
from app.schemas.common import CustomAttribute


class BeforeResponse(CustomAttribute):
    vehicle_tasks: list[VehicleTasks] = Field()
    unassigned: list[str] = Field()


class AfterResponse(CustomAttribute):
    before_tasks: list[VehicleTasks] = Field(default_factory=list)
    after_tasks: list[VehicleTasks] = Field(default_factory=list)
    swaps: list[VehicleSwaps] = Field(default_factory=list)
