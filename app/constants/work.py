from enum import StrEnum


class WorkStatus(StrEnum):
    """
    아무 액션도 없는 상태
    (`pickup.location`에 있음)
    """

    WAITING = "waiting"

    """
    vehicle_id 차량에 실려있음
    (`vehicle.current_location`에 있음)
    """
    SHIPPED = "shipped"

    """
    실려가다가 어떠한 사유로 내려짐
    (`location`에 있음, 차량 고장 등으로 다른 차가 처리 필요할 때)
    """
    STOPPED = "stopped"

    """
    완료
    (`location`에 있음, 특별한 사유가 없다면 `delivery.location`과 같다)
    """
    DONE = "done"


class TaskType(StrEnum):
    JOB = "job"
    PICKUP = "pickup"
    DELIVERY = "delivery"
    ARRIVAL = "arrival"
    DEPARTURE = "departure"
    WAITING = "waiting"
    SHIPMENT_PICKUP = "shipment_pickup"
    SHIPMENT_DELIVERY = "shipment_delivery"
    END = "end"


class RoutingProfile(StrEnum):
    CAR = "car"
    ATLAN = "atlan"


class StepType(StrEnum):
    START = "start"
    JOB = "job"
    END = "end"
