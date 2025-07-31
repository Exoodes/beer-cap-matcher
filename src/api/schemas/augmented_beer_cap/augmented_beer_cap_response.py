from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class AugmentedBeerCapResponse(BaseModel):
    id: int
    embedding_vector: Optional[List[float]] = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")
