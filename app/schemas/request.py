from datetime import datetime, timedelta

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    model_validator,
)
from app.constants.work import WorkStatus
from app.models.coordinate import Coordinate


class Status(BaseModel):
    type: WorkStatus = Field(default=WorkStatus.WAITING)
    vehicle_id: int | None = Field(default=None)
    location: Coordinate | None = Field(default=None)


class WorkPoint(BaseModel):
    location: Coordinate
    setup_time: timedelta = Field(default=timedelta(minutes=0))
    service_time: timedelta = Field(default=timedelta(minutes=5))
    group_id: str | None = Field(default=None)

    @property
    def get_setup_time(self) -> int:
        return int(self.setup_time.total_seconds())

    @property
    def get_service_time(self) -> int:
        return int(self.service_time.total_seconds())


class Assembly(BaseModel):
    model_config: ConfigDict = ConfigDict(from_attributes=True)

    id: str
    location: list[float]
    capacity: int | None = Field(default=0)


class Boundary(BaseModel):
    id: str
    polygon: list[list[float]]


class Work(BaseModel):
    id: str
    pickup: WorkPoint
    delivery: WorkPoint
    amount: list[int] | None = Field(default=None)
    status: Status | None = Field(default=Status)
    excepotion: bool | None = Field(default=False)
    fix_vehicle_id: str | None = Field(default=None)

    @model_validator(mode="before")
    @classmethod
    def vehicle_id_validator(cls, values, info: ValidationInfo):
        if values.get("exception") and not values.get("fix_vehicle_id"):
            raise ValueError("fix_vehicle_id required")
        return values


class Vehicle(BaseModel):
    id: str
    profile: str | None = "car"
    current_location: Coordinate
    include: list[str]
    exclude: list[str]
    home: Coordinate | None = Field(default=None)

    @property
    def location_to_dict(self) -> dict:
        return self.current_location.to_dict()


class JejuRequest(BaseModel):
    current_time: datetime
    works: list[Work]
    vehicles: list[Vehicle]
    assemblies: list[Assembly]
    boundaries: list[Boundary]
