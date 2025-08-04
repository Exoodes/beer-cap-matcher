from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AugmentedBeerCapResponseBase(BaseModel):
    """
    Base response schema for an augmented beer cap,
    including its ID and optional embedding vector.
    """

    id: int = Field(..., description="ID of the augmented beer cap")
    embedding_vector: Optional[List[float]] = Field(
        default=None, description="Embedding vector representing the image features"
    )

    model_config = ConfigDict(from_attributes=True, extra="forbid")
