from typing import NoReturn

from fastapi import HTTPException


def api_error(status_code: int, code: str, message: str) -> NoReturn:
    """Single error shape for the whole API: {"detail": {"code", "message"}}."""
    raise HTTPException(status_code=status_code, detail={"code": code, "message": message})
