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
    _index_to_id: dict[tuple[str, str], int] = {}
    _id_to_index: dict[int, tuple[str, str]] = {}

    def get_id(self, index: dict) -> int:
        """
        return id to use index
        index : (status, works_id)
        """
        return self._index_to_id[index]

    def get_index(self, id: int) -> dict:
        """
        return index to use id
        index : (status, works_id)
        """
        return self._id_to_index[id]

    def set(self, role: ROLE, id: str) -> int:
        """
        ROLE : "pickup", "delivery", "shipment_pickup", "shipment_delivery", "shipment_assembly", "vehicle",
        """
        key = (role, id)
        if key not in self._index_to_id:
            self._id_to_index[self._unique_id] = key
            self._index_to_id[key] = self._unique_id
            self._unique_id += 1
        return self._index_to_id[key]
