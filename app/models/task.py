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
    vehicle_id: str = Field()
    assembly_id: str = Field()
    stop_over_time: NonNegativeInt = Field(serialization_alias="stopover_time")
    up: list[str] | None = Field(default_factory=list)
    down: list[str] | None = Field(default_factory=list)
