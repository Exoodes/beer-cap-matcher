from pydantic import BaseModel, ConfigDict, Field


class AugmentedCapCreateSchema(BaseModel):
    filename: str = Field(..., description="File name of the augmented image")

    model_config = ConfigDict(from_attributes=True)
