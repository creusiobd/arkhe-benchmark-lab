"""Structured local validation errors for observable journeys."""

class TrajectoryError(ValueError):
    """Base error; messages contain configuration paths, never event contents."""

class ConfigurationError(TrajectoryError):
    pass

class EventValidationError(TrajectoryError):
    pass

class EventRejectedError(EventValidationError):
    """Engine refused the input before any trajectory state changed; safe to retry or drop."""

class DuplicateEventError(EventRejectedError):
    pass
