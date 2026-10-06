"""Local example: no tools, network calls or financial transactions."""
from datetime import datetime, timedelta, timezone
import json
from arkhe_defense import (DefenseSDK, InMemoryPolicyProvider, PolicySnapshot,
    PolicyRule, ResourcePattern, RuntimeContext, ActionProposed,
    ActionCompleted, ApprovalRecorded, hash_action)

def main():
    now = datetime.now(timezone.utc)
    provider = InMemoryPolicyProvider()
    sdk = DefenseSDK(provider, clock=lambda: now)
    for tenant in ('client-a', 'client-b'):
        def context(role, principal, producer, scope):
            return RuntimeContext(tenant_id=tenant, authority=role,
                principal_id=principal, producer_id=producer,
                scopes=frozenset({'events:write', scope}))
        admin = context('policy_admin', 'admin', 'admin', 'policy:write')
        policy = PolicySnapshot(tenant_id=tenant, policy_id='reconciliation',
            version='v1', mission='Reconcile authorized ledger records', rules=(
                PolicyRule(rule_id='read', tool_name='ledger', action_type='read',
                    allowed_resources=(ResourcePattern(kind='path_prefix', value='/ledger'),)),
                PolicyRule(rule_id='write', tool_name='ledger', action_type='write',
                    allowed_resources=(ResourcePattern(kind='exact', value='/ledger/authorized'),), requires_approval=True)))
        provider.register(policy, admin, activate=True)
        agent = context('agent', 'agent1', 'agent', 'actions:propose')
        approver = context('approver', 'human1', 'approver', 'approvals:write')
        executor = context('executor', 'worker1', 'executor', 'actions:complete')
        def common(event_id, producer='agent'):
            return dict(event_id=event_id, tenant_id=tenant, trajectory_id='run1',
                agent_id='agent1', occurred_at=now, ingested_at=now, producer_id=producer)
        def show(event, ctx):
            decision = sdk.ingest(event, ctx)
            print(json.dumps(decision.model_dump(mode='json'), ensure_ascii=True))
        read = ActionProposed(**common('read1'), action_id='read1', tool_name='ledger',
            action_type='read', target_resource='/ledger/invoices', policy_version='v1')
        show(read, agent)
        write = ActionProposed(**common('write1'), action_id='write1', tool_name='ledger',
            action_type='write', target_resource='/ledger/authorized', policy_version='v1')
        show(write, agent)
        approval = ApprovalRecorded(**common('approval1', 'approver'), approval_id='approval1',
            action_id=write.action_id, action_hash=hash_action(write), policy_version='v1',
            expires_at=now + timedelta(minutes=5))
        show(approval, approver)
        show(ActionCompleted(**common('completed1', 'executor'), action_id=write.action_id,
            proposal_event_id=write.event_id, status='success'), executor)
        forbidden = ActionProposed(**common('external1'), action_id='external1', tool_name='http',
            action_type='network', target_resource='https://external.example', policy_version='v1')
        show(forbidden, agent)
        show(ActionCompleted(**common('external-completed', 'executor'), action_id=forbidden.action_id,
            proposal_event_id=forbidden.event_id, status='success'), executor)

if __name__ == '__main__':
    main()
