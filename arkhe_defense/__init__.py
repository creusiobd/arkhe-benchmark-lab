"""Local defensive observation SDK; host authentication is required upstream."""
from .contracts import (ActionProposed, ActionCompleted, ApprovalRecorded,
    PolicyChanged, TrajectoryClosed, RuntimeContext, Authority, ActionType,
    CompletionStatus, Decision, DecisionStatus, Event, parse_event)
from .config import SDKConfig, StateLimits
from .policy import (PolicySnapshot, PolicyRule, ResourcePattern,
    PolicyProvider, InMemoryPolicyProvider, hash_action)
from .errors import DefenseError, AuthorityError, PolicyError, EventConflictError
from .evaluator import DefenseEvaluator, DefenseSDK, Evaluator
from .state import BoundedStateStore
from .exporters import JSONLExporter
from .journal import DurableDefenseSession, JournalError

__all__ = ['ActionProposed', 'ActionCompleted', 'ApprovalRecorded', 'PolicyChanged',
    'TrajectoryClosed', 'RuntimeContext', 'Authority', 'ActionType', 'CompletionStatus',
    'Decision', 'DecisionStatus', 'Event', 'parse_event', 'SDKConfig', 'StateLimits',
    'PolicySnapshot', 'PolicyRule', 'ResourcePattern', 'PolicyProvider',
    'InMemoryPolicyProvider', 'hash_action', 'DefenseError', 'AuthorityError',
    'PolicyError', 'EventConflictError', 'DefenseEvaluator', 'DefenseSDK',
    'BoundedStateStore', 'JSONLExporter', 'Evaluator', 'DurableDefenseSession', 'JournalError']

__version__ = '0.2.0'
