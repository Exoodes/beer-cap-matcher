from typing import Optional

from pydantic import BaseModel, ConfigDict


class BeerCapUpdateSchema(BaseModel):
    variant_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")
