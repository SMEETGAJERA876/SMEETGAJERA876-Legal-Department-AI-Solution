class AppError(Exception):
    """An error with a user-facing message, rendered as {"error": code, "message": message}."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class NotFoundError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(404, "not_found", message)


class ValidationError(AppError):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(status_code, code, message)
