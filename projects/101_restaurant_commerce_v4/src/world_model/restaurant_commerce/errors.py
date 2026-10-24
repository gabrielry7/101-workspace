class CommerceError(Exception):
    """Base restaurant-commerce error."""


class NotFoundError(CommerceError):
    pass


class ValidationError(CommerceError):
    pass


class InvalidTransitionError(CommerceError):
    pass


class PaymentError(CommerceError):
    pass


class DeliveryError(CommerceError):
    pass


class IdempotencyConflictError(CommerceError):
    pass


class ConcurrencyConflictError(CommerceError):
    pass


class AuthenticationError(CommerceError):
    pass


class RetryableProviderError(CommerceError):
    """Provider failed in a way explicitly declared safe to retry."""


class ProviderCircuitOpenError(CommerceError):
    pass
