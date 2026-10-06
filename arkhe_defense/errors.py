"""Errors never imply a healthy observation or an execution authorization."""
class DefenseError(ValueError):
    pass

class AuthorityError(DefenseError):
    pass

class PolicyError(DefenseError):
    pass

class EventConflictError(DefenseError):
    pass
