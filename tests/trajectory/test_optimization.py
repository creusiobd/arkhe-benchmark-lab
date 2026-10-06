import unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch,PropertyMock
from arkhe_trajectory import JourneyConfig,JourneyStep,ThresholdRule,TrajectoryEvent,JourneyEngine
from arkhe_trajectory.errors import ConfigurationError

class OptimizationTests(unittest.TestCase):
 def config(self,limit=32,rules=None):
  return JourneyConfig(tenant_id='t',journey_id='j',version='1',steps=(JourneyStep('s'),),window_seconds=10,baseline={'x':100.},rules=rules or tuple(ThresholdRule(rule_id=f'r{i}',metric='x',operator='gt',threshold=0,aggregation='mean') for i in range(32)),ttl_seconds=1000,max_events=1000,max_evidence_refs=limit)
 def event(self,i,x=200.):
  at=datetime(2026,10,6,12,tzinfo=timezone.utc)+timedelta(seconds=i)
  return TrajectoryEvent('t','j','1','run',f'e{i}','s',at,at,{'x':x})
 def test_refs_bounded_full_sample_count_historical_idempotence(self):
  config=self.config(3);now=datetime(2026,10,6,13,tzinfo=timezone.utc)
  engine=JourneyEngine(config,clock=lambda:now)
  first=engine.ingest(self.event(0))
  for i in range(1,100):last=engine.ingest(self.event(i))
  self.assertEqual(last.findings[0].sample_count,11)
  self.assertEqual(last.findings[0].elapsed_seconds,10)
  self.assertTrue(last.findings[0].evidence_truncated)
  self.assertEqual(last.findings[0].evidence_event_ids,('e97','e98','e99'))
  self.assertIs(engine.ingest(self.event(0)),first)
  refs=sum(len(f.evidence_event_ids) for state in engine.state.trajectories.values() for assessment in state.assessments.values() for f in assessment.findings)
  self.assertLessEqual(refs,100*32*3)
 def test_equivalent_rules_share_aggregate_but_thresholds_separate(self):
  import arkhe_trajectory.engine as module
  engine=JourneyEngine(self.config(),clock=lambda:datetime(2026,10,6,13,tzinfo=timezone.utc))
  with patch.object(module,'aggregate',wraps=module.aggregate) as call:
   result=engine.ingest(self.event(0))
  self.assertEqual(len(result.findings),32)
  self.assertEqual(call.call_count,2) # global trend + one mean for all equivalent rules
 def test_configuration_hash_is_cached(self):
  engine=JourneyEngine(self.config(),clock=lambda:datetime(2026,10,6,13,tzinfo=timezone.utc))
  original=engine.config.configuration_hash
  with patch.object(JourneyConfig,'configuration_hash',new_callable=PropertyMock,side_effect=AssertionError('recomputed')):
   self.assertEqual(engine.ingest(self.event(0)).configuration_hash,original)
 def test_config_positive_evidence_limit_and_roundtrip(self):
  for limit in (0,-1,True,1.5):
   with self.subTest(limit=limit),self.assertRaises(ConfigurationError):self.config(limit)
  self.assertEqual(JourneyConfig.from_dict(self.config(7).to_dict()).max_evidence_refs,7)
 def test_structural_findings_budget_preserves_deviation_and_complete_count(self):
  config=JourneyConfig(tenant_id='t',journey_id='j',version='1',steps=(JourneyStep('s'),JourneyStep('other')),window_seconds=1000,baseline={'x':100.},rules=(ThresholdRule('metric','x','gt',100000),),ttl_seconds=2000,max_events=1000,max_evidence_refs=1,max_findings=8)
  now=datetime(2026,10,6,12,3,tzinfo=timezone.utc);engine=JourneyEngine(config,clock=lambda:now)
  from dataclasses import replace
  for i in range(100):last=engine.ingest(replace(self.event(i),step_id='s' if i%2==0 else 'other'))
  self.assertEqual(last.status,'deviation')
  self.assertEqual(last.total_findings,99)
  self.assertTrue(last.findings_truncated)
  self.assertEqual(len(last.findings),8)
  self.assertTrue(all(f.evidence_truncated for f in last.findings))
  self.assertEqual(last.findings[-1].sample_count,2)
  self.assertEqual(last.findings[-1].evidence_event_ids,('e99',))
  assessments=next(iter(engine.state.trajectories.values())).assessments.values()
  self.assertLessEqual(sum(len(a.findings) for a in assessments),100*8)
  self.assertLessEqual(sum(len(f.evidence_event_ids) for a in assessments for f in a.findings),100*8*1)

 def test_numeric_equivalence_window_persistence_step_reference(self):
  # Independent mathematical oracle: statistics mean/regression, explicit window prefixes.
  from statistics import mean,linear_regression
  rules=tuple(ThresholdRule(rule_id=f'{agg}-{ref}-{persist}',metric='x',operator='gt',threshold=0.01 if ref=='relative' else 0.,aggregation=agg,reference=ref,min_samples=2 if agg=='slope' else 1,persistence=persist,step_id='s') for agg in ['latest','mean','max','min','slope'] for ref in (['absolute'] if agg=='slope' else ['absolute','delta','relative']) for persist in [1,3])
  config=self.config(1000,rules);now=self.event(0).event_time
  engine=JourneyEngine(config,clock=lambda:now)
  def measure(rule,samples):
   if len(samples)<rule.min_samples:return None,None
   xs,ys=zip(*samples)
   number=(ys[-1] if rule.aggregation=='latest' else mean(ys) if rule.aggregation=='mean' else max(ys) if rule.aggregation=='max' else min(ys) if rule.aggregation=='min' else linear_regression(xs,ys).slope)
   comparison=number if rule.reference=='absolute' else number-100 if rule.reference=='delta' else (number-100)/100
   return number,comparison
  values=[100+(i%7)*10 for i in range(30)]
  for i,value in enumerate(values):
   now=self.event(i).event_time;result=engine.ingest(self.event(i,value))
   samples=[(j,values[j]) for j in range(max(0,i-10),i+1)]
   expected={}
   for rule in rules:
    number,comparison=measure(rule,samples)
    holds=number is not None and comparison>rule.threshold
    if holds and rule.persistence>1:
     holds=len(samples)>=rule.persistence and all((lambda pair:pair[1] is not None and pair[1]>rule.threshold)(measure(rule,samples[:k+1])) for k in range(len(samples)-rule.persistence,len(samples)))
    if holds:expected[rule.rule_id]=(number,comparison)
   self.assertEqual({f.rule_id for f in result.findings},set(expected))
   for finding in result.findings:
    number,comparison=expected[finding.rule_id]
    self.assertAlmostEqual(finding.observed,number,places=8)
    self.assertAlmostEqual(finding.comparison_value,comparison,places=8)
    self.assertEqual(finding.sample_count,len(samples))
    self.assertEqual(finding.evidence_event_ids,tuple(f'e{j}' for j,_ in samples))
  historical=engine.check('t','run',as_of=self.event(24).event_time)
  self.assertTrue(all(f.sample_count==11 for f in historical.findings))
  self.assertEqual(historical.window_end,self.event(24).event_time)


if __name__=='__main__':unittest.main()
