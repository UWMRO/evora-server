from dataclasses import dataclass, field
import json 
import numpy as np
from enum import Enum


class PlateSolvingResultStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass
class PlateSolvingResult():
    status: PlateSolvingResultStatus
    failure_reason: str = None

    center_ra_deg: float = 0.0
    center_dec_deg: float = 0.0
    visualization_url: str = None