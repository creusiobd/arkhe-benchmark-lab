"""Structured local validation errors for observable journeys."""

class TrajectoryError(ValueError):
    """Base error; messages contain configuration paths, never event contents."""

class ConfigurationError(TrajectoryError):
    pass

class EventValidationError(TrajectoryError):
    pass

class DuplicateEventError(EventValidationError):
    pass
