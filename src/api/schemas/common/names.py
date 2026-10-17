from typing import Annotated, Any

from pydantic import BeforeValidator


def clean_name(value: Any) -> Any:
    """Trims and collapses inner whitespace: "  Bernard   12° " -> "Bernard 12°"."""
    return " ".join(value.split()) if isinstance(value, str) else value


# Names of beers, brands and countries. Stored cleaned, so names that differ
# only in spacing can't become separate entries.
CleanName = Annotated[str, BeforeValidator(clean_name)]
