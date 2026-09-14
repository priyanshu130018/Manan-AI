class MananException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ValidationError(MananException):
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class AuthenticationError(MananException):
    def __init__(self, message: str = "Authentication failed.", status_code: int = 401):
        super().__init__(message, status_code=status_code)


class InvalidCredentialsError(AuthenticationError):
    def __init__(self, message: str = "Invalid email or password."):
        super().__init__(message, status_code=401)


class DuplicateEntityError(MananException):
    def __init__(self, message: str = "Entity already exists."):
        super().__init__(message, status_code=409)


class EntityNotFoundError(MananException):
    def __init__(self, message: str = "Entity not found.", status_code: int = 404):
        super().__init__(message, status_code=status_code)


class DocumentError(MananException):
    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message, status_code=status_code)


class DocumentValidationError(ValidationError):
    def __init__(self, message: str):
        super().__init__(message)


class DocumentProcessingError(DocumentError):
    def __init__(self, message: str):
        super().__init__(message, status_code=422)


class OCRProcessingError(DocumentError):
    def __init__(self, message: str):
        super().__init__(message, status_code=422)


class AIServiceError(MananException):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message, status_code=status_code)


class RateLimitError(AIServiceError):
    def __init__(self, message: str = "Rate limit reached. Please wait before retrying.", retry_after: float = 30.0):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class LLMError(AIServiceError):
    def __init__(self, message: str):
        super().__init__(message, status_code=503)


class EmbeddingError(AIServiceError):
    def __init__(self, message: str):
        super().__init__(message, status_code=502)


class RetrievalError(MananException):
    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class PersistenceError(MananException):
    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class SessionNotFoundError(EntityNotFoundError):
    def __init__(self, session_id: str):
        super().__init__(f"Session '{session_id}' not found.", status_code=404)


class DocumentNotFoundError(EntityNotFoundError):
    def __init__(self, document_id: str):
        super().__init__(f"Document '{document_id}' not found.", status_code=404)


class UserNotFoundError(EntityNotFoundError):
    def __init__(self, user_id: str):
        super().__init__(f"User '{user_id}' not found.", status_code=404)
