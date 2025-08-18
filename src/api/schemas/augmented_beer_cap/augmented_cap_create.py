from pydantic import BaseModel, ConfigDict, Field


class AugmentedCapCreateSchema(BaseModel):
    """
    Input schema for creating a new augmented beer cap image,
    including the filename reference.
    """

    filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="File name of the augmented image",
    )

    model_config = ConfigDict(from_attributes=True)
