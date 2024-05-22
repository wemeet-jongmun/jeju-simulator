RELAY_VEHICLE_TIME: int = 1800
DELIVERY_DRIVERS: dict[str, dict[str, list[str]]] = {
    "기사 A": {"include": ["A-0"], "exclude": ["A-1", "A2B", "AD"]},
    "기사 B": {"include": ["B-0"], "exclude": ["B-1"]},
    "기사 C": {"include": ["C-0"], "exclude": ["C-1"]},
    "기사 D": {"include": ["D-0"], "exclude": ["D-1", "CD"]},
    "기사 E": {"include": ["E"], "exclude": []},
    "기사 F": {"include": ["F"], "exclude": []},
}
