"""Domain errors that the API maps to HTTP status codes."""


class NotFoundError(Exception):
    """A referenced entity does not exist (mapped to 404)."""
