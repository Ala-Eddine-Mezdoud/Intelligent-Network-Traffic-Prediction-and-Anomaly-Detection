"""Protocol schemas."""
from pydantic import BaseModel


class ProtocolDistributionItem(BaseModel):
    name: str
    value: int


class ProtocolDistributionResponse(BaseModel):
    data: list[ProtocolDistributionItem]
