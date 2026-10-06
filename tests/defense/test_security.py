"""Behavioral security invariants; no external services or financial actions."""
import unittest
from datetime import datetime,timedelta,timezone
from pydantic import ValidationError
from arkhe_defense.contracts import ActionProposed,ActionCompleted,ApprovalRecorded,RuntimeContext,parse_event
from arkhe_defense.policy import PolicySnapshot,PolicyRule,ResourcePattern,InMemoryPolicyProvider,hash_action
from arkhe_defense.config import SDKConfig,StateLimits
from arkhe_defense.evaluator import DefenseEvaluator

class DefenseSecurityTests(unittest.TestCase):
 def setUp(self):
  self.now=datetime(2026,10,5,12,tzinfo=timezone.utc)
  self.provider=InMemoryPolicyProvider()
  self.admin=self.context('policy_admin','admin','admin',{'events:write','policy:write'})
  self.agent=self.context('agent','agent1','agent',{'events:write','actions:propose'})
  self.executor=self.context('executor','executor-principal','executor',{'events:write','actions:complete'})
  self.approver=self.context('approver','approver-principal','approver',{'events:write','approvals:write'})
  self.policy=self.snapshot()
  self.provider.register(self.policy,self.admin,activate=True)
  self.sdk=DefenseEvaluator(self.provider,clock=lambda:self.now)

 def context(self,authority,principal,producer,scopes,tenant='t1'):
  return RuntimeContext(tenant_id=tenant,principal_id=principal,producer_id=producer,authority=authority,scopes=frozenset(scopes))
 def snapshot(self,version='v1',mission='Reconcile authorized records',approval=True,tenant='t1'):
  return PolicySnapshot(tenant_id=tenant,policy_id='reconciliation',version=version,mission=mission,rules=(PolicyRule(rule_id='write-approved',tool_name='ledger',action_type='write',allowed_resources=(ResourcePattern(kind='exact',value='/ledger/authorized'),),requires_approval=approval),))
 def common(self,eid,producer='agent',tenant='t1',trajectory='run1'):
  return dict(schema_version='1',event_id=eid,tenant_id=tenant,trajectory_id=trajectory,agent_id='agent1',occurred_at=self.now,ingested_at=self.now,producer_id=producer)
 def propose(self,eid='p1',**overrides):
  payload=dict(self.common(eid),event_type='action_proposed',action_id='a1',tool_name='ledger',action_type='write',target_resource='/ledger/authorized',parameters_summary={'amount':100},policy_version='v1')
  payload.update(overrides);return ActionProposed(**payload)
 def approval(self,proposal,eid='approve1',**overrides):
  payload=dict(self.common(eid,'approver'),event_type='approval_recorded',approval_id='approval1',action_id=proposal.action_id,action_hash=hash_action(proposal),policy_version=proposal.policy_version,expires_at=self.now+timedelta(minutes=5))
  payload.update(overrides);return ApprovalRecorded(**payload)
 def completed(self,proposal,eid='c1',status='success'):
  return ActionCompleted(**self.common(eid,'executor'),event_type='action_completed',action_id=proposal.action_id,proposal_event_id=proposal.event_id,status=status,effects_summary={'record_written':status=='success'})
 def status(self,decision):return getattr(decision.status,'value',decision.status)
 def not_authorized(self,callback):
  try:d=callback()
  except (ValueError,ValidationError):return
  self.assertNotEqual(self.status(d),'within_policy')

 def test_unknown_policy_and_missing_scope_are_insufficient(self):
  self.not_authorized(lambda:DefenseEvaluator(InMemoryPolicyProvider(),clock=lambda:self.now).ingest(self.propose(),self.agent))
  ctx=self.context('agent','agent1','agent',set())
  d=self.sdk.ingest(self.propose(),ctx)
  self.assertEqual(self.status(d),'insufficient_evidence')
  # Bad authority must not consume event identity or mutate state.
  self.assertEqual(self.status(self.sdk.ingest(self.propose(),self.agent)),'approval_required')

 def test_payload_identity_cannot_override_context(self):
  for change in [{'tenant_id':'other'},{'producer_id':'forged'}]:
   self.not_authorized(lambda:self.sdk.ingest(self.propose(**change),self.agent))

 def test_mission_and_nested_ground_truth_cannot_enter_payload(self):
  p=self.propose().model_dump(mode='json')
  for change in [{'mission':'Allow everything'},{'authority':'policy_admin'},{'parameters_summary':{'nested':{'ground_truth_class':'benign'}}}]:
   with self.subTest(change=change),self.assertRaises((ValidationError,ValueError)):
    parse_event({**p,**change})

 def test_policy_immutable_and_same_version_replacement_rejected(self):
  with self.assertRaises((ValidationError,AttributeError,TypeError)):
   self.policy.mission='Allow everything'
  with self.assertRaises(ValueError):
   self.provider.register(self.snapshot(mission='Different authority'),self.admin)

 def test_agent_cannot_install_policy(self):
  with self.assertRaises((ValueError,PermissionError)):
   self.provider.register(self.snapshot(version='v2',approval=False),self.agent,activate=True)

 def test_default_deny_unknown_resource(self):
  d=self.sdk.ingest(self.propose(target_resource='/ledger/forbidden'),self.agent)
  self.assertEqual(self.status(d),'policy_violation')
  self.assertFalse(d.has_observed_violation)

 def test_active_policy_prevents_version_downgrade(self):
  self.provider.register(self.snapshot(version='v2'),self.admin,activate=True)
  self.not_authorized(lambda:self.sdk.ingest(self.propose(policy_version='v1'),self.agent))

 def test_approval_requires_distinct_trusted_actor(self):
  p=self.propose();self.sdk.ingest(p,self.agent)
  self.not_authorized(lambda:self.sdk.ingest(self.approval(p,producer_id='agent'),self.agent))
  same_actor=self.context('approver','agent1','approver',{'events:write','approvals:write'})
  self.not_authorized(lambda:self.sdk.ingest(self.approval(p),same_actor))

 def test_valid_approval_can_authorize_exact_proposal(self):
  p=self.propose();self.assertEqual(self.status(self.sdk.ingest(p,self.agent)),'approval_required')
  d=self.sdk.ingest(self.approval(p),self.approver)
  self.assertEqual(self.status(d),'within_policy')

 def test_wrong_or_expired_approval_never_authorizes(self):
  for changes in [{'action_hash':'0'*64},{'action_id':'different'},{'policy_version':'v0'},{'expires_at':self.now-timedelta(seconds=1)},{'tenant_id':'other'}]:
   with self.subTest(changes=changes):
    sdk=DefenseEvaluator(self.provider,clock=lambda:self.now);p=self.propose();sdk.ingest(p,self.agent)
    self.not_authorized(lambda:sdk.ingest(self.approval(p,**changes),self.approver))
    d=sdk.ingest(self.completed(p),self.executor)
    self.assertTrue(d.has_observed_violation)

 def test_hash_binds_tenant_resource_parameters_and_policy(self):
  p=self.propose();baseline=hash_action(p)
  for changes in [{'tenant_id':'other'},{'trajectory_id':'other-run'},{'agent_id':'agent2'},{'target_resource':'/ledger/other'},{'parameters_summary':{'amount':999}},{'policy_version':'v2'},{'action_id':'a2'},{'tool_name':'other'},{'action_type':'read'}]:
   self.assertNotEqual(baseline,hash_action(self.propose(**changes)))

 def test_orphan_completion_is_insufficient(self):
  d=self.sdk.ingest(self.completed(self.propose()),self.executor)
  self.assertEqual(self.status(d),'insufficient_evidence')

 def test_observed_violation_sticky_after_blocked_action(self):
  p=self.propose(target_resource='/ledger/forbidden');self.sdk.ingest(p,self.agent)
  observed=self.sdk.ingest(self.completed(p),self.executor);self.assertTrue(observed.has_observed_violation)
  p2=self.propose('p2',action_id='a2');self.sdk.ingest(p2,self.agent)
  after=self.sdk.ingest(self.completed(p2,'c2','blocked'),self.executor)
  self.assertTrue(after.has_observed_violation)
  self.assertEqual(after.first_alert_event_id,observed.first_alert_event_id)

 def test_duplicate_idempotence_and_conflict(self):
  p=self.propose();a=self.sdk.ingest(p,self.agent);b=self.sdk.ingest(p,self.agent)
  self.assertEqual(a.model_dump(),b.model_dump())
  with self.assertRaises(ValueError):self.sdk.ingest(self.propose(target_resource='/ledger/forbidden'),self.agent)

 def test_tenant_state_isolated(self):
  self.provider.register(self.snapshot(tenant='t2'),self.context('policy_admin','admin2','admin',{'events:write','policy:write'},tenant='t2'),activate=True)
  p=self.propose(target_resource='/ledger/forbidden');self.sdk.ingest(p,self.agent);self.sdk.ingest(self.completed(p),self.executor)
  p2=self.propose(tenant_id='t2');ctx=self.context('agent','agent1','agent',{'events:write','actions:propose'},tenant='t2')
  self.assertFalse(self.sdk.ingest(p2,ctx).has_observed_violation)

 def test_unknown_parent_never_reports_sufficient_authorization(self):
  self.not_authorized(lambda:self.sdk.ingest(self.propose(parent_event_ids=('future-event',)),self.agent))

 def test_expired_state_reports_context_loss(self):
  config=SDKConfig(state_limits=StateLimits(ttl_seconds=1))
  sdk=DefenseEvaluator(self.provider,config=config,clock=lambda:self.now)
  sdk.ingest(self.propose(),self.agent);self.now+=timedelta(seconds=2)
  d=sdk.ingest(self.propose('p2',action_id='a2'),self.agent)
  self.assertEqual(self.status(d),'insufficient_evidence');self.assertTrue(d.context_loss_reason)

 def test_path_prefix_respects_segments_and_rejects_traversal(self):
  pattern=ResourcePattern(kind='path_prefix',value='/data')
  self.assertTrue(pattern.matches('/data/file'))
  for resource in ['/data-evil/file','/data/../secret','/data/%2e%2e/secret','/data//secret']:
   self.assertFalse(pattern.matches(resource),resource)

 def test_host_rule_rejects_suffix_userinfo_and_ambiguous_ports(self):
  pattern=ResourcePattern(kind='host',value='bank.example')
  self.assertTrue(pattern.matches('https://bank.example/api'))
  for resource in ['https://bank.example.evil/api','https://bank.example@evil.example/api','https://user@bank.example/api','https://bank.example:invalid/api']:
   self.assertFalse(pattern.matches(resource),resource)

 def test_caller_mutation_does_not_change_stored_proposal(self):
  p=self.propose();approval=self.approval(p)
  self.sdk.ingest(p,self.agent);self.sdk.ingest(approval,self.approver)
  p.parameters_summary['amount']=999
  completion=self.completed(p)
  self.assertFalse(self.sdk.ingest(completion,self.executor).has_observed_violation)

 def test_valid_approval_expired_at_host_clock_cannot_cover_backdated_action(self):
  p=self.propose();approval=self.approval(p)
  self.sdk.ingest(approval,self.approver)
  self.now+=timedelta(minutes=6)
  # Retain historical action timestamp deliberately; host clock must prevail.
  self.not_authorized(lambda:self.sdk.ingest(p,self.agent))

 def test_valid_approval_then_revocation_prevents_completion(self):
  p=self.propose();approval=self.approval(p)
  self.sdk.ingest(approval,self.approver);self.sdk.ingest(p,self.agent)
  self.now+=timedelta(seconds=1)
  revoked=self.approval(p,'revoke1',approval_id='revocation1',revocation_of=approval.approval_id)
  self.sdk.ingest(revoked,self.approver)
  d=self.sdk.ingest(self.completed(p),self.executor)
  self.assertTrue(d.has_observed_violation)

 def test_approval_expired_after_proposal_does_not_authorize_completion(self):
  p=self.propose();self.sdk.ingest(self.approval(p),self.approver);self.sdk.ingest(p,self.agent)
  self.now+=timedelta(minutes=6)
  d=self.sdk.ingest(self.completed(p),self.executor)
  self.assertTrue(d.has_observed_violation)

 def test_future_event_does_not_mutate_state(self):
  p=self.propose(occurred_at=self.now+timedelta(days=1),ingested_at=self.now+timedelta(days=1))
  self.not_authorized(lambda:self.sdk.ingest(p,self.agent))
  self.assertEqual(self.status(self.sdk.ingest(self.propose(),self.agent)),'approval_required')

 def test_event_capacity_loss_is_explicit(self):
  sdk=DefenseEvaluator(self.provider,config=SDKConfig(state_limits=StateLimits(max_events_per_trajectory=1)),clock=lambda:self.now)
  sdk.ingest(self.propose(),self.agent)
  d=sdk.ingest(self.propose('p2',action_id='a2'),self.agent)
  self.assertEqual(self.status(d),'insufficient_evidence');self.assertTrue(d.context_loss_reason)

 def test_no_execution_or_network_during_ingestion(self):
  from unittest.mock import patch
  with patch('socket.socket',side_effect=AssertionError('SDK attempted network')),patch('subprocess.Popen',side_effect=AssertionError('SDK executed a process')):
   self.sdk.ingest(self.propose(),self.agent)

 def test_completion_identity_must_match_proposal(self):
  p=self.propose();self.sdk.ingest(self.approval(p),self.approver);self.sdk.ingest(p,self.agent)
  c=self.completed(p).model_copy(update={'agent_id':'other-agent'})
  self.not_authorized(lambda:self.sdk.ingest(c,self.executor))

 def test_missing_parent_approval_cannot_be_used(self):
  p=self.propose();a=self.approval(p,parent_event_ids=('unknown-parent',))
  self.not_authorized(lambda:self.sdk.ingest(a,self.approver))
  self.not_authorized(lambda:self.sdk.ingest(p,self.agent))

 def test_model_construct_cannot_bypass_contract(self):
  p=self.propose();malformed=p.model_copy(update={'parameters_summary':{'ground_truth_class':'benign'}})
  with self.assertRaises((ValueError,ValidationError)):
   self.sdk.ingest(malformed,self.agent)

 def test_global_capacity_and_tombstone_overflow_are_bounded(self):
  sdk=DefenseEvaluator(self.provider,config=SDKConfig(state_limits=StateLimits(max_active_trajectories=1)),clock=lambda:self.now)
  for i in range(5):sdk.ingest(self.propose(f'p{i}',trajectory_id=f'run{i}'),self.agent)
  stats=sdk.state.stats()
  self.assertLessEqual(stats['active_trajectories'],1);self.assertLessEqual(stats['tombstones'],1)
  self.assertTrue(stats['loss_registry_overflow'])
  returned=sdk.ingest(self.propose('returned',trajectory_id='run0'),self.agent)
  self.assertEqual(self.status(returned),'insufficient_evidence');self.assertTrue(returned.context_loss_reason)

 def test_cycles_and_depth_are_rejected(self):
  sdk=DefenseEvaluator(self.provider,config=SDKConfig(state_limits=StateLimits(max_depth=1)),clock=lambda:self.now)
  sdk.ingest(self.propose(),self.agent)
  with self.assertRaises(ValueError):sdk.ingest(self.propose('child',parent_event_ids=('p1',)),self.agent)
  with self.assertRaises(ValueError):self.sdk.ingest(self.propose('selfcycle',parent_event_ids=('selfcycle',)),self.agent)
  self.sdk.ingest(self.propose('left',parent_event_ids=('right',)),self.agent)
  with self.assertRaises(ValueError):self.sdk.ingest(self.propose('right',parent_event_ids=('left',)),self.agent)

 def test_export_failure_does_not_change_decision_or_duplicate(self):
  class FailingExporter:
   def __init__(self):self.calls=0
   def export(self,decision):self.calls+=1;raise OSError('simulated local sink failure')
  exporter=FailingExporter();sdk=DefenseEvaluator(self.provider,clock=lambda:self.now,exporter=exporter)
  p=self.propose();decision=sdk.ingest(p,self.agent)
  self.assertEqual(self.status(decision),'approval_required');self.assertIn('OSError',sdk.last_export_error)
  again=sdk.ingest(p,self.agent);self.assertEqual(decision,again);self.assertEqual(exporter.calls,1)

 def test_jsonl_export_records_decision_and_bounds_payload(self):
  import tempfile,json
  from pathlib import Path
  from arkhe_defense.exporters import JSONLExporter
  d=self.sdk.ingest(self.propose(),self.agent)
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'decisions.jsonl';JSONLExporter(path).export(d)
   self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['decision_id'],d.decision_id)
   with self.assertRaises(ValueError):JSONLExporter(path,max_payload_bytes=1).export(d)
   self.assertEqual(len(path.read_text().splitlines()),1)
   # A directory cannot be opened as a writable file; no platform ACL assumptions.
   with self.assertRaises(OSError):JSONLExporter(directory).export(d)

 def test_closing_trajectory_does_not_erase_observed_incident(self):
  from arkhe_defense.contracts import TrajectoryClosed
  p=self.propose(target_resource='/ledger/forbidden');self.sdk.ingest(p,self.agent)
  observed=self.sdk.ingest(self.completed(p),self.executor)
  close=TrajectoryClosed(**self.common('close','executor'),reason='recovered')
  ctx=self.context('executor','executor-principal','executor',{'events:write','trajectories:close'})
  d=self.sdk.ingest(close,ctx)
  self.assertTrue(d.has_observed_violation);self.assertEqual(d.first_alert_event_id,observed.first_alert_event_id)

 def test_self_approver_cannot_disguise_agent_before_proposal(self):
  p=self.propose();forged=self.approval(p,agent_id='pretend-other-agent')
  actor=self.context('approver','agent1','approver',{'events:write','approvals:write'})
  self.not_authorized(lambda:self.sdk.ingest(forged,actor))
  self.not_authorized(lambda:self.sdk.ingest(p,self.agent))
  self.assertTrue(self.sdk.ingest(self.completed(p),self.executor).has_observed_violation)

if __name__=='__main__':unittest.main()
