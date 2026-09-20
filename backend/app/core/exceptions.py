class ApplicationError(Exception):
    status_code = 500

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ResourceNotFoundError(ApplicationError):
    status_code = 404


class ConflictError(ApplicationError):
    status_code = 409


class DomainValidationError(ApplicationError):
    status_code = 422


class PersistenceError(ApplicationError):
    status_code = 500


class FileTooLargeError(ApplicationError):
    status_code = 413


class ProcessMiningError(ApplicationError):
    status_code = 500
