from typing import Optional

from pydantic import BaseModel, ConfigDict


class BeerCapUpdateSchema(BaseModel):
    variant_name: Optional[str]

    model_config = ConfigDict(from_attributes=True)
