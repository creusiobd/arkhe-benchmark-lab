"""Errors never imply a healthy observation or an execution authorization."""
class DefenseError(ValueError):
    pass

class AuthorityError(DefenseError):
    pass

class PolicyError(DefenseError):
    pass

class EventRejectedError(DefenseError):
    """Invalid input refused before any evaluator state changed; safe to retry or drop."""

class EventConflictError(EventRejectedError):
    pass
