from typing import ClassVar

from pydantic import BaseModel, model_validator


class PartialUpdateSchema(BaseModel):
    """Base for PATCH bodies.

    Omitted fields are left unchanged and ``null`` clears a nullable field.
    Fields listed in ``non_nullable_fields`` reject an explicit ``null``.
    """

    non_nullable_fields: ClassVar[tuple[str, ...]] = ()

    @model_validator(mode="after")
    def _reject_null_for_required_fields(self):
        for field in self.non_nullable_fields:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self
