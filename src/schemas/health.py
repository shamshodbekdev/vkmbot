from dataclasses import dataclass


@dataclass
class HealthSchema:
    database: bool
    queue: bool
    cache: bool
    bot: bool
