from enum import StrEnum
from typing import Literal

ROLE = Literal[
    "pickup",
    "delivery",
    "shipment_pickup",
    "shipment_delivery",
    "shipment_assembly",
    "vehicle",
]


class IdHandler:
    """
    Pickup, Delivery, Vehicle Mapping용 Identity 부여
    """

    _unique_id: int = 0
    _id_to_index: dict[tuple[str, str], int] = {}
    _index_to_id: dict[int, tuple[str, str]] = {}

    def get_from_id(self, id: int) -> dict:
        return self._id_to_index[id]

    def get_from_index(self, index: dict) -> int:
        return self._index_to_id[index]

    def set(self, role: ROLE, id: str) -> int:
        """
        ROLE : "pickup", "delivery", "shipment_pickup", "shipment_delivery", "shipment_assembly", "vehicle",
        """
        key = (role, id)
        if key not in self._id_to_index:
            self._id_to_index[key] = self._unique_id
            self._index_to_id[self._unique_id] = key
            self._unique_id += 1
        return self._id_to_index[key]
