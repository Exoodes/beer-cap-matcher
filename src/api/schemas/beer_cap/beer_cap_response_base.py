from typing import Optional

from pydantic import BaseModel, ConfigDict


class BeerCapResponseBase(BaseModel):
    id: int
    variant_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")
