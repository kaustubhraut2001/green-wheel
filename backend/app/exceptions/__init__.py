"""
Domain-specific exceptions.

Using typed exceptions instead of bare HTTPException inside services keeps
the service layer decoupled from HTTP — services should not know about HTTP
status codes. The exception middleware translates these into HTTP responses.
"""


class AppException(Exception):
    """Base exception for all application errors."""
    def __init__(self, message: str, code: str = "APP_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundException(AppException):
    def __init__(self, resource: str, identifier: str = ""):
        super().__init__(
            message=f"{resource} not found" + (f": {identifier}" if identifier else ""),
            code="NOT_FOUND",
        )


class ConflictException(AppException):
    def __init__(self, message: str):
        super().__init__(message=message, code="CONFLICT")


class AuthenticationException(AppException):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message=message, code="AUTHENTICATION_FAILED")


class AuthorizationException(AppException):
    def __init__(self, message: str = "You do not have permission to perform this action"):
        super().__init__(message=message, code="FORBIDDEN")


class InsufficientFundsException(AppException):
    def __init__(self, available: str, required: str, currency: str):
        super().__init__(
            message=f"Insufficient funds. Available: {available} {currency}, Required: {required} {currency}",
            code="INSUFFICIENT_FUNDS",
        )


class WalletSuspendedException(AppException):
    def __init__(self, wallet_id: str):
        super().__init__(
            message=f"Wallet {wallet_id} is suspended or closed",
            code="WALLET_SUSPENDED",
        )


class DuplicateTransactionException(AppException):
    """Raised when an idempotency key has already been processed."""
    def __init__(self, key: str):
        super().__init__(
            message=f"Transaction with idempotency key '{key}' already processed",
            code="DUPLICATE_TRANSACTION",
        )


class ExchangeRateUnavailableException(AppException):
    def __init__(self, from_currency: str, to_currency: str):
        super().__init__(
            message=f"Exchange rate unavailable for {from_currency} → {to_currency}",
            code="EXCHANGE_RATE_UNAVAILABLE",
        )


class RateLimitException(AppException):
    def __init__(self, message: str = "Too many requests. Please try again later."):
        super().__init__(message=message, code="RATE_LIMIT_EXCEEDED")


class ValidationException(AppException):
    def __init__(self, message: str):
        super().__init__(message=message, code="VALIDATION_ERROR")


class CircuitOpenException(AppException):
    def __init__(self, service: str):
        super().__init__(
            message=f"Service '{service}' is temporarily unavailable. Falling back to cached data.",
            code="CIRCUIT_OPEN",
        )
