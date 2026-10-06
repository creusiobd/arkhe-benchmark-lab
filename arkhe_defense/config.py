"""Bounded observation configuration; no execution or network effects."""
from typing import Annotated, Literal
from pydantic import Field, StrictInt
from .contracts import FrozenModel

PositiveInt = Annotated[StrictInt, Field(gt=0)]

class StateLimits(FrozenModel):
    ttl_seconds: PositiveInt = 1800
    max_active_trajectories: PositiveInt = 10000
    max_events_per_trajectory: PositiveInt = 1000
    max_parent_ids: PositiveInt = 16
    max_depth: PositiveInt = 128

class SDKConfig(FrozenModel):
    schema_version: Literal['1'] = '1'
    mode: Literal['observe'] = 'observe'
    state_limits: StateLimits = Field(default_factory=StateLimits)
    max_payload_bytes: PositiveInt = 65536
