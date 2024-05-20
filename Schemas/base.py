import random
from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field

from Constants.enum import WorkStatus
from Constants.vehicles import DELIVERY_DRIVERS
from Utils import (
    generate_random_boolean,
    get_random_4_number,
    get_random_jeju_coordinates,
    get_random_korean_string,
    get_random_seconds,
)


class Coordinate(BaseModel):
    longitude: float = Field(default=(random.uniform(126.0, 128.0)))
    latitude: float = Field(default=(random.uniform(35.0, 38.0)))


class Status(BaseModel):
    type: WorkStatus = Field(default=WorkStatus.waiting)
    vehicle_id: int | None = Field(default=None)
    location: Coordinate | None = Field(default=None)


class WorkPoint(BaseModel):
    location: Coordinate
    setup_time: timedelta = Field(default=timedelta(minutes=0))
    service_time: timedelta = Field(default=timedelta(minutes=5))
    group_id: str | None = Field(default=None)


class Assembly(BaseModel):
    model_config: ConfigDict = ConfigDict(from_attributes=True)

    id: str
    location: list[float]
    capacity: int | None = Field(default=0)

    def __init__(self):
        """
        제주 축산 농협 하나로마트 아라점 기점으로 임시 선언
        """
        self.id = "센터"
        self.location = [33.5110502, 126.5209303]


class Boundary(BaseModel):
    id: str
    polygon: list[list[float]]


class Work(BaseModel):
    model_config: ConfigDict = ConfigDict(from_attributes=True)

    id: str
    pickup: WorkPoint
    delivery: WorkPoint
    amount: list[int] | None = Field(default=None)
    status: Status | None = Field(default=Status)
    excepotion: bool | None = Field(default=False)
    fix_vehicle_id: str | None = Field(default=None)


class Vehicle(BaseModel):
    model_config: ConfigDict = ConfigDict(from_attributes=True)

    id: str
    profile: str | None = "car"
    current_location: list[float]
    include: list[str]
    exclude: list[str]
    home: Coordinate | None = Field(default=None)

    def __init__(self, driver_id: str):
        self.id = DELIVERY_DRIVERS[driver_id]
        self.current_location = get_random_jeju_coordinates()
        self.include = DELIVERY_DRIVERS[driver_id]["include"]
        self.exclude = DELIVERY_DRIVERS[driver_id]["exclude"]


class Request(BaseModel):
    current_time: datetime
    works: list[Work]
    vehicles: list[Vehicle]
    assemblies: list[Assembly]
    boundaries: list[Boundary]

    def __init__(self, work_cnt: int = 1):
        _current_time = datetime.now()
        _setup_time = f"PT{get_random_seconds(1)}S"
        _service_time = f"PT{get_random_seconds(3)}S"

        _works = [
            Work(
                id=f"{get_random_4_number()}_{get_random_korean_string()}",
                pickup=LocationTime(
                    location=get_random_jeju_coordinates(),
                    setup_time=_setup_time,
                    service_time=_service_time,
                ),
                delivery=LocationTime(
                    location=get_random_jeju_coordinates(),
                    setup_time=_setup_time,
                    service_time=_service_time,
                ),
                status=Status(type="waiting"),
                excepotion=generate_random_boolean(),
            )
            for _ in range(work_cnt)
        ]

        _vehicles = [Vehicle(driver_id=key) for key in DELIVERY_DRIVERS.keys]

        self.current_time = _current_time
        self.works = _works
        self.vehicles = _vehicles

    def __repr__(self) -> str:
        return super().__repr__(f"Request")


class Skills:
    __unique_skill_id: int
    __skills: dict[str, int]
    __waves: list[int]
    __vehicles: list[int]
    __group_vehicles: dict[str, set[tuple[int, int]]]
    __assembly_visits: dict[int, dict[str, dict[int, set[int]]]]

    def __init__(
        self,
        vehicles: list[Vehicle],
    ) -> None:
        self.__unique_skill_id = 0
        self.__skills = {}
        self.__vehicles = [v.id for v in vehicles]
        self.__group_vehicles = {}
        self.__assembly_visits = {}

    def add_key(self, key: str):
        if key not in self.__skills:
            self.__skills[key] = self.__unique_skill_id
            self.__unique_skill_id += 1
