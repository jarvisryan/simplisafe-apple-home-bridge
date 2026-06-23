from __future__ import annotations


def http_status(error: BaseException) -> int | None:
    current: object = error
    visited: set[int] = set()
    while isinstance(current, BaseException) and id(current) not in visited:
        visited.add(id(current))
        status = getattr(current, "status", None)
        if isinstance(status, int):
            return status
        cause = current.__cause__ or current.__context__
        if cause is None and current.args and isinstance(current.args[0], BaseException):
            cause = current.args[0]
        current = cause
    return None


def safe_error_message(error: BaseException) -> str:
    """Return a useful message without serialising third-party request objects."""
    if isinstance(error, (OSError, RuntimeError, ValueError)):
        return str(error)
    if (status := http_status(error)) is not None:
        return f"{type(error).__name__} (HTTP {status})"
    return type(error).__name__
