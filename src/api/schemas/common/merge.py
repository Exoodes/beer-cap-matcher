from pydantic import BaseModel, ConfigDict, Field


class MergeSchema(BaseModel):
    """Body of a merge: the entry that the merged one is folded into."""

    into_id: int = Field(..., ge=1, description="ID of the entry to merge into")

    model_config = ConfigDict(extra="forbid")
