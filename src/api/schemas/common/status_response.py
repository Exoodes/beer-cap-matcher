from pydantic import BaseModel, Field


class StatusResponse(BaseModel):
    """
    Common status response indicating success or failure of an operation.
    """

    success: bool = Field(..., description="True if the operation was successful")
    message: str = Field(
        ..., description="Human-readable message about the operation result"
    )
