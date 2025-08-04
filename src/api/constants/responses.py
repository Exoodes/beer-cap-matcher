from typing import Dict

ResponseDict = Dict[int, dict]

ERROR_DESCRIPTIONS = {
    401: "Unauthorized",
    403: "Forbidden",
    404: "Resource not found",
    500: "Internal server error",
}

INTERNAL_SERVER_ERROR_RESPONSE: ResponseDict = {
    500: {"description": ERROR_DESCRIPTIONS[500]}
}

NOT_FOUND_RESPONSE: ResponseDict = {
    404: {"description": ERROR_DESCRIPTIONS[404]}
}

UNAUTHORIZED_RESPONSE: ResponseDict = {
    401: {"description": ERROR_DESCRIPTIONS[401]}
}

DEFAULT_ERROR_RESPONSES: ResponseDict = {
    code: {"description": desc}
    for code, desc in ERROR_DESCRIPTIONS.items()
    if code in {401, 403, 500}
}
