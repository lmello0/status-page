from enum import Enum


class StatusType(str, Enum):
    OPERATIONAL = "OPERATIONAL"
    DEGRADED = "DEGRADED"
    OUTAGE = "OUTAGE"

    @property
    def severity(self) -> int:
        mapping = {
            StatusType.OUTAGE: 2,
            StatusType.DEGRADED: 1,
            StatusType.OPERATIONAL: 0,
        }

        return mapping[self]
