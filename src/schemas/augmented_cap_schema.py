from pydantic import BaseModel, Field


class AugmentedCapCreateSchema(BaseModel):
    filename: str = Field(..., description="File name of the augmented image")

    class Config:
        from_attributes = True
