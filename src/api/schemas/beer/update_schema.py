from typing import Optional

from pydantic import BaseModel, ConfigDict


class BeerUpdateSchema(BaseModel):
    name: Optional[str]

    model_config = ConfigDict(from_attributes=True)
