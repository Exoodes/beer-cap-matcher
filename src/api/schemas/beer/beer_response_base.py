from pydantic import BaseModel, ConfigDict


class BeerResponseBase(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True, extra="forbid")
