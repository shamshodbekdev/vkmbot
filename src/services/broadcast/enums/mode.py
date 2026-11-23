from enum import Enum


class BroadcastMode(str, Enum):
    FORWARD = "forward"
    COPY = "copy"