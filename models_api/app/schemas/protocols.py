"""Protocol schemas."""
from typing import List

from pydantic import BaseModel


class ProtocolDistributionItem(BaseModel):
    name: str
    value: int


class ProtocolDistributionResponse(BaseModel):
    data: List[ProtocolDistributionItem]
