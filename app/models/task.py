from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt

from app.constants.work import TaskType
from app.models.coordinate import Coordinate


class Task(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    work_id: str | None = Field(None)
    type: TaskType = Field()
    eta: NonNegativeInt = Field(default=0)
    duration: NonNegativeInt = Field(default=0)
    distance: NonNegativeInt = Field(default=0)
    setup_time: NonNegativeInt = Field(default=0)
    service_time: NonNegativeInt = Field(default=0)
    assembly_id: str | None = Field(None)
    location: Coordinate = Field()


class VehicleTasks(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vehicle_id: str = Field()
    tasks: list[Task] = Field()


class VehicleSwaps(BaseModel):
    vehicle_id: str
    assembly_id: str
    stopover_time: NonNegativeInt
    down: list[str]
    up: list[str]
