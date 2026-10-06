"""Deterministic observation only. Serial evaluator; never executes or authorizes tools."""
from datetime import datetime, timezone
import hashlib
import json

from .contracts import Decision, parse_event, RuntimeContext, utc_datetime
from .errors import DefenseError, EventConflictError, PolicyError
from .config import SDKConfig
from .policy import hash_action
from .state import BoundedStateStore


def _value(value):
    return getattr(value, "value", value)


class DefenseEvaluator:
    def __init__(self, policy_provider, config=None, clock=None, state=None, exporter=None):
        self.policy_provider = policy_provider
        self.config = config or SDKConfig()
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.state = state or BoundedStateStore(self.config.state_limits, self.clock)
        self.exporter = exporter
        self.last_export_error = None

    def _decision(self, event, status, state=None, policy=None, rules=(), evidence=(), missing=()):
        identity = f"{event.tenant_id}\0{event.trajectory_id}\0{event.event_id}"
        return Decision(
            decision_id=hashlib.sha256(identity.encode()).hexdigest(), event_id=event.event_id,
            tenant_id=event.tenant_id, trajectory_id=event.trajectory_id, status=status,
            policy_version=policy.version if policy else None,
            policy_hash=policy.policy_hash if policy else None,
            rule_ids=tuple(rules), evidence_refs=tuple(evidence or (event.event_id,)),
            missing_fields=tuple(missing), context_loss_reason=state.context_loss_reason if state else None,
            has_observed_violation=state.observed_violation if state else False,
            first_alert_event_id=state.first_alert_event_id if state else None,
        )

    def _publish(self, decision):
        self.last_export_error = None
        if self.exporter:
            try:
                self.exporter.export(decision)
            except Exception as error:
                self.last_export_error = f"{type(error).__name__}: {error}"
        return decision

    def _trusted(self, event, context):
        authority = _value(context.authority)
        required = {
            "action_proposed": ({"agent", "executor"}, "actions:propose"),
            "action_completed": ({"executor"}, "actions:complete"),
            "approval_recorded": ({"approver", "supervisor"}, "approvals:write"),
            "policy_changed": ({"policy_admin"}, "policy:write"),
            "trajectory_closed": ({"supervisor", "executor"}, "trajectories:close"),
        }
        roles, scope = required[_value(event.event_type)]
        return (context.tenant_id == event.tenant_id and context.producer_id == event.producer_id
                and bool(context.principal_id) and authority in roles
                and "events:write" in context.scopes and scope in context.scopes
                and (authority != "agent" or context.principal_id == event.agent_id)
                and (authority not in {"approver", "supervisor"} or _value(event.event_type) != "approval_recorded"
                     or context.principal_id != event.agent_id))

    def _cycle(self, event, state):
        pending = list(event.parent_event_ids)
        seen = set()
        while pending:
            parent = pending.pop()
            if parent == event.event_id:
                return True
            if parent not in seen:
                seen.add(parent)
                if parent in state.events:
                    pending.extend(state.events[parent].parent_event_ids)
        return False

    def _approval(self, action, policy, state, now, cutoff=None):
        cutoff = cutoff or action.occurred_at
        candidates = [e for e in state.events.values()
                      if _value(e.event_type) == "approval_recorded" and e.action_id == action.action_id]
        if not candidates:
            return "approval_required", ()
        revocations = {e.revocation_of for e in candidates if e.revocation_of
                       and e.occurred_at <= cutoff and e.ingested_at <= cutoff
                       and state.received_at[e.event_id] <= now
                       and e.action_hash == hash_action(action) and e.policy_version == policy.version
                       and (_value(state.decisions[e.event_id].status) == "within_policy"
                            or state.decisions[e.event_id].missing_fields == ("approval_action_pending",))}
        for approval in candidates:
            recorded = state.decisions[approval.event_id]
            pending_binding = recorded.missing_fields == ("approval_action_pending",)
            if approval.revocation_of or (_value(recorded.status) != "within_policy" and not pending_binding):
                continue
            if (approval.approval_id not in revocations and approval.action_hash == hash_action(action)
                    and approval.policy_version == policy.version
                    and approval.agent_id == action.agent_id
                    and state.principals[approval.event_id] != action.agent_id
                    and approval.occurred_at <= cutoff
                    and approval.ingested_at <= cutoff
                    and state.received_at[approval.event_id] <= now
                    and approval.expires_at > cutoff and approval.expires_at > now):
                return "within_policy", (approval.event_id,)
        return "insufficient_evidence", tuple(e.event_id for e in candidates)

    def ingest(self, event, context):
        event = parse_event(event).model_copy(deep=True)
        context = RuntimeContext.model_validate(context).model_copy(deep=True)
        encoded = json.dumps(event.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        if len(encoded.encode()) > self.config.max_payload_bytes:
            raise DefenseError("event exceeds maximum payload bytes")
        if not self._trusted(event, context):
            return self._publish(self._decision(event, "insufficient_evidence", missing=("trusted_context",)))
        now = utc_datetime(self.clock())
        if event.occurred_at > now or event.ingested_at > now:
            return self._publish(self._decision(event, "insufficient_evidence", missing=("future_event_time",)))
        state = self.state.get((event.tenant_id, event.trajectory_id), now)
        fingerprint = hashlib.sha256(encoded.encode()).hexdigest()
        if event.event_id in state.fingerprints:
            if state.fingerprints[event.event_id] != fingerprint:
                raise EventConflictError("event_id reused with conflicting payload")
            return state.decisions[event.event_id]
        if self._cycle(event, state):
            raise DefenseError("event graph contains a cycle")
        if len(event.parent_event_ids) > self.config.state_limits.max_parent_ids:
            raise DefenseError("parent count exceeds configured maximum")
        if len(state.events) >= self.config.state_limits.max_events_per_trajectory:
            self.state.mark_event_capacity(state)
            return self._publish(self._decision(event, "insufficient_evidence", state, missing=("event_capacity",)))
        depth = 1 + max((state.depths.get(p, 0) for p in event.parent_event_ids), default=0)
        if depth > self.config.state_limits.max_depth:
            raise DefenseError("event graph depth exceeds configured maximum")
        missing_parents = tuple(p for p in event.parent_event_ids if p not in state.events
                                or state.events[p].occurred_at > event.occurred_at
                                or any(field.startswith("parent:") for field in state.decisions[p].missing_fields))
        state.events[event.event_id] = event
        state.fingerprints[event.event_id] = fingerprint
        state.received_at[event.event_id] = now
        state.principals[event.event_id] = context.principal_id
        state.depths[event.event_id] = depth
        try:
            policy = self.policy_provider.get_active(event.tenant_id)
        except PolicyError:
            policy = None
        status, rules, evidence, missing = "within_policy", (), (event.event_id,), ()
        kind = _value(event.event_type)
        if state.context_loss_reason:
            status, missing = "insufficient_evidence", ("trajectory_context",)
        elif missing_parents:
            status, missing = "insufficient_evidence", tuple(f"parent:{p}" for p in missing_parents)
        elif policy is None:
            status, missing = "insufficient_evidence", ("active_policy",)
        elif kind == "action_proposed":
            if event.policy_version != policy.version:
                status, missing = "insufficient_evidence", ("active_policy_version",)
            else:
                matched = tuple(r for r in policy.rules if r.matches(event))
                rules = tuple(r.rule_id for r in matched)
                if not matched:
                    status = "policy_violation"
                elif any(r.requires_approval for r in matched):
                    status, refs = self._approval(event, policy, state, now)
                    evidence += refs
                    if status == "insufficient_evidence":
                        missing = ("valid_scoped_approval",)
        elif kind == "action_completed":
            proposal = state.events.get(event.proposal_event_id)
            prior = state.decisions.get(event.proposal_event_id)
            if (proposal is None or _value(proposal.event_type) != "action_proposed"
                    or proposal.action_id != event.action_id or proposal.agent_id != event.agent_id or prior is None):
                status, missing = "insufficient_evidence", ("matching_proposal",)
            elif proposal.occurred_at > event.occurred_at or prior.policy_version != policy.version or prior.policy_hash != policy.policy_hash:
                status, missing = "insufficient_evidence", ("proposal_temporal_policy_context",)
            elif _value(prior.status) == "insufficient_evidence" and any(
                item not in {"valid_scoped_approval"} for item in prior.missing_fields):
                status, missing = "insufficient_evidence", ("proposal_evidence",)
            else:
                evidence += prior.evidence_refs
                matched = tuple(r for r in policy.rules if r.matches(proposal))
                rules = tuple(r.rule_id for r in matched)
                permitted = bool(matched)
                if permitted and any(r.requires_approval for r in matched):
                    approval_status, refs = self._approval(proposal, policy, state, now, cutoff=event.occurred_at)
                    evidence += refs
                    permitted = approval_status == "within_policy"
                if _value(event.status) == "success" and not permitted:
                    status = "policy_violation"
                    state.observed_violation = True
        elif kind == "approval_recorded":
            known = [e for e in state.events.values() if _value(e.event_type) == "action_proposed" and e.action_id == event.action_id]
            if (event.policy_version != policy.version or event.expires_at <= now
                    or any(event.action_hash != hash_action(p) or event.agent_id != p.agent_id
                           or context.principal_id == p.agent_id for p in known)):
                status, missing = "insufficient_evidence", ("approval_policy_hash_or_expiry",)
            elif not known:
                status, missing = "insufficient_evidence", ("approval_action_pending",)
        elif kind == "policy_changed":
            if event.policy_version != policy.version or event.policy_hash != policy.policy_hash:
                status, missing = "insufficient_evidence", ("trusted_active_policy_snapshot",)
        if status in {"policy_violation", "approval_required"} and state.first_alert_event_id is None:
            state.first_alert_event_id = event.event_id
        decision = self._decision(event, status, state, policy, rules, evidence, missing)
        state.decisions[event.event_id] = decision
        return self._publish(decision)


DefenseSDK = DefenseEvaluator
Evaluator = DefenseEvaluator
