from pydantic import BaseModel


class DeleteStatusResponse(BaseModel):
    success: bool
    message: str
