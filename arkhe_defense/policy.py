"""Immutable policy versions and structured, deny-by-default resource matching."""
import hashlib
import json
import re
from threading import RLock
from typing import Literal, Protocol
from urllib.parse import unquote, urlsplit
from pydantic import Field, StrictBool, model_validator
from .contracts import ActionProposed, ActionType, Authority, FrozenModel, Identifier, RuntimeContext
from .errors import AuthorityError, PolicyError

def canonical_path(value: str) -> str:
    if not isinstance(value, str) or not value or '\x00' in value:
        raise ValueError('nonempty absolute path required')
    value = value.replace('\\', '/')
    decoded = unquote(value)
    if decoded != value:
        raise ValueError('percent-encoded paths are not supported')
    parts = value.split('/')
    if any(part in ('.', '..') for part in parts):
        raise ValueError('relative path components prohibited')
    windows = bool(re.match(r'^[A-Za-z]:/', value))
    if not windows and not value.startswith('/'):
        raise ValueError('absolute path required')
    if value.startswith('//') or '//' in value:
        raise ValueError('ambiguous separators or UNC paths unsupported')
    if ':' in (value[2:] if windows else value):
        raise ValueError('alternate data streams/URI paths unsupported')
    normalized = value if windows and len(value) == 3 else (value.rstrip('/') or '/')
    return normalized.casefold() if windows else normalized

def canonical_host(value: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError('DNS hostname required')
    if any(character in value for character in '/\\:@*?#%'):
        raise ValueError('hostname must not contain URI, port, wildcard or escapes')
    host = value.rstrip('.').encode('idna').decode('ascii').lower()
    if len(host) > 253 or not all(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label)
                                for label in host.split('.')):
        raise ValueError('invalid DNS hostname')
    return host

def target_host(resource: str) -> str:
    if '://' not in resource:
        return canonical_host(resource)
    parsed = urlsplit(resource)
    if parsed.scheme not in ('https', 'http') or parsed.username or parsed.password or not parsed.hostname:
        raise ValueError('unsupported network resource')
    # Invalid ports must not accidentally fall through as an allowed host.
    parsed.port
    return canonical_host(parsed.hostname)

class ResourcePattern(FrozenModel):
    kind: Literal['exact', 'path_prefix', 'host']
    value: Identifier

    @model_validator(mode='after')
    def canonical(self):
        canonical = (canonical_path(self.value) if self.kind == 'path_prefix' else
                     canonical_host(self.value) if self.kind == 'host' else self.value)
        object.__setattr__(self, 'value', canonical)
        return self

    def matches(self, resource: str) -> bool:
        try:
            if self.kind == 'exact':
                return resource == self.value
            if self.kind == 'host':
                return target_host(resource) == self.value
            path = canonical_path(resource)
            return path == self.value or path.startswith(self.value.rstrip('/') + '/')
        except (ValueError, UnicodeError):
            return False

class PolicyRule(FrozenModel):
    rule_id: Identifier
    tool_name: Identifier
    action_type: ActionType
    allowed_resources: tuple[ResourcePattern, ...] = ()
    requires_approval: StrictBool = False

    def matches(self, action: ActionProposed) -> bool:
        return (action.tool_name == self.tool_name and action.action_type == self.action_type
                and any(resource.matches(action.target_resource) for resource in self.allowed_resources))

class PolicySnapshot(FrozenModel):
    tenant_id: Identifier
    policy_id: Identifier
    version: Identifier
    mission: str = Field(min_length=1, max_length=8192, strict=True)
    rules: tuple[PolicyRule, ...] = ()

    @model_validator(mode='after')
    def unique_rules(self):
        if len({rule.rule_id for rule in self.rules}) != len(self.rules):
            raise ValueError('duplicate policy rule IDs')
        return self

    @property
    def policy_hash(self) -> str:
        return _hash(self.model_dump(mode='json'))

def _hash(data) -> str:
    encoded = json.dumps(data, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, allow_nan=False).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()

def hash_action(action: ActionProposed) -> str:
    """Bind approval to exact action, policy and tenant, independent of telemetry IDs."""
    return _hash({name: getattr(action, name) for name in (
        'tenant_id', 'trajectory_id', 'agent_id', 'action_id', 'tool_name', 'action_type', 'target_resource',
        'parameters_summary', 'policy_version')})

class PolicyProvider(Protocol):
    def get(self, tenant_id: str, version: str) -> PolicySnapshot: ...
    def get_active(self, tenant_id: str) -> PolicySnapshot: ...
    def active_version(self, tenant_id: str) -> str: ...

class InMemoryPolicyProvider:
    """Host-owned registry; mutation requires a separately authenticated admin."""
    def __init__(self):
        self._snapshots: dict[tuple[str, str], PolicySnapshot] = {}
        self._active: dict[str, str] = {}
        self._lock = RLock()

    @staticmethod
    def _authorize(tenant_id: str, context: RuntimeContext):
        if (context.tenant_id != tenant_id or context.authority != Authority.POLICY_ADMIN
                or 'policy:write' not in context.scopes):
            raise AuthorityError('policy mutation requires tenant policy_admin with policy:write')

    def register(self, snapshot: PolicySnapshot, context: RuntimeContext, *, activate: bool = False):
        self._authorize(snapshot.tenant_id, context)
        snapshot = PolicySnapshot.model_validate(snapshot.model_dump(mode='python'))
        with self._lock:
            key = (snapshot.tenant_id, snapshot.version)
            prior = self._snapshots.get(key)
            if prior is not None and prior.policy_hash != snapshot.policy_hash:
                raise PolicyError('immutable policy version conflict')
            self._snapshots[key] = snapshot
            if activate:
                self._active[snapshot.tenant_id] = snapshot.version

    def activate(self, tenant_id: str, version: str, context: RuntimeContext):
        self._authorize(tenant_id, context)
        with self._lock:
            self.get(tenant_id, version)
            self._active[tenant_id] = version

    def get(self, tenant_id: str, version: str) -> PolicySnapshot:
        with self._lock:
            try:
                return self._snapshots[(tenant_id, version)]
            except KeyError:
                raise PolicyError('policy version unavailable for tenant') from None

    def active_version(self, tenant_id: str) -> str:
        with self._lock:
            try:
                return self._active[tenant_id]
            except KeyError:
                raise PolicyError('active policy unavailable for tenant') from None

    def get_active(self, tenant_id: str) -> PolicySnapshot:
        with self._lock:
            return self.get(tenant_id, self.active_version(tenant_id))
