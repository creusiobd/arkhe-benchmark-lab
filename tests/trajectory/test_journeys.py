"""Independent local behavior tests; synthetic signals are not predictive evidence."""
import unittest
from datetime import datetime,timedelta,timezone
from arkhe_trajectory import TrajectoryEvent,JourneyStep,ThresholdRule,JourneyConfig,JourneyEngine

class JourneyTests(unittest.TestCase):
 def setUp(self):
  self.now=datetime(2026,10,6,12,tzinfo=timezone.utc)
  self.config=self.configuration()
  self.engine=JourneyEngine(self.config,clock=lambda:self.now)
 def configuration(self,**changes):
  data=dict(tenant_id='bank1',journey_id='authorization',version='v1',
   steps=(JourneyStep(step_id='start',expected_next=('finish',),max_delay_seconds=10),JourneyStep(step_id='finish')),
   window_seconds=60,baseline={'latency':100.0},
   rules=(ThresholdRule(rule_id='latency-max',metric='latency',operator='gt',threshold=120.0,severity='warning',aggregation='latest'),),
   ttl_seconds=120,max_events=20,max_trajectories=10,max_lateness_seconds=0)
  data.update(changes);return JourneyConfig(**data)
 def event(self,eid='e1',**changes):
  data=dict(tenant_id='bank1',journey_id='authorization',journey_version='v1',trajectory_id='txn1',event_id=eid,step_id='start',event_time=self.now,ingested_at=self.now,metrics={'latency':100.0},dimensions={})
  data.update(changes);return TrajectoryEvent(**data)
 def status(self,a):return getattr(a.status,'value',a.status)
 def rejected_or_insufficient(self,callback):
  try:a=callback()
  except ValueError:return
  self.assertEqual(self.status(a),'insufficient_evidence')

 def test_threshold_observation_is_explicit_deviation(self):
  a=self.engine.ingest(self.event(metrics={'latency':150.0}))
  self.assertEqual(self.status(a),'deviation');self.assertTrue(a.findings)

 def test_missing_metric_is_not_zero_or_healthy(self):
  a=self.engine.ingest(self.event(metrics={}))
  self.assertEqual(self.status(a),'insufficient_evidence')

 def test_single_sample_cannot_prove_trend(self):
  a=self.engine.ingest(self.event())
  self.assertNotIn('latency',a.trends)

 def test_historical_slope_depends_on_event_time_not_arrival(self):
  self.engine.ingest(self.event())
  self.now+=timedelta(seconds=10)
  a=self.engine.ingest(self.event('e2',metrics={'latency':110.0}))
  self.assertAlmostEqual(a.trends['latency'],1.0)

 def test_declining_and_constant_sequences_are_not_rising(self):
  for values in [(110.0,100.0),(100.0,100.0)]:
   engine=JourneyEngine(self.config,clock=lambda:self.now)
   earlier=self.now-timedelta(seconds=10)
   engine.ingest(self.event('first',metrics={'latency':values[0]},event_time=earlier,ingested_at=earlier))
   a=engine.ingest(self.event('last',metrics={'latency':values[1]}))
   self.assertLessEqual(a.trends['latency'],0.0)

 def test_mean_rule_distinguishes_same_latest_value_history(self):
  rule=ThresholdRule(rule_id='mean',metric='latency',operator='gt',threshold=105.0,severity='warning',aggregation='mean')
  config=self.configuration(rules=(rule,))
  high=JourneyEngine(config,clock=lambda:self.now);low=JourneyEngine(config,clock=lambda:self.now)
  past=self.now-timedelta(seconds=5)
  high.ingest(self.event('h1',event_time=past,ingested_at=past,metrics={'latency':150.0}))
  low.ingest(self.event('l1',event_time=past,ingested_at=past,metrics={'latency':50.0}))
  a=high.ingest(self.event('h2',metrics={'latency':100.0}));b=low.ingest(self.event('l2',metrics={'latency':100.0}))
  self.assertEqual(self.status(a),'deviation');self.assertNotEqual(self.status(b),'deviation')

 def test_duplicate_exact_idempotent_and_conflict_rejected(self):
  e=self.event();a=self.engine.ingest(e);b=self.engine.ingest(e)
  self.assertEqual(a,b)
  with self.assertRaises(ValueError):self.engine.ingest(self.event(metrics={'latency':999.0}))

 def test_config_tenant_journey_version_mismatch_rejected(self):
  for change in [{'tenant_id':'other'},{'journey_id':'other'},{'journey_version':'v0'}]:
   self.rejected_or_insufficient(lambda:self.engine.ingest(self.event(**change)))

 def test_trajectory_histories_do_not_mix(self):
  self.engine.ingest(self.event(metrics={'latency':150.0}))
  self.now+=timedelta(seconds=5)
  other=self.engine.ingest(self.event('other',trajectory_id='txn2',metrics={'latency':100.0}))
  self.assertNotIn('latency',other.trends);self.assertNotEqual(self.status(other),'deviation')

 def test_future_event_cannot_enter_history(self):
  future=self.now+timedelta(days=1)
  self.rejected_or_insufficient(lambda:self.engine.ingest(self.event(event_time=future,ingested_at=future)))
  a=self.engine.ingest(self.event());self.assertNotIn('latency',a.trends)

 def test_out_of_order_does_not_silently_report_normal(self):
  self.engine.ingest(self.event())
  past=self.now-timedelta(seconds=1)
  self.rejected_or_insufficient(lambda:self.engine.ingest(self.event('late',event_time=past)))

 def test_window_uses_event_time_and_excludes_old_history(self):
  rule=ThresholdRule(rule_id='mean',metric='latency',operator='gt',threshold=120.0,severity='warning',aggregation='mean')
  engine=JourneyEngine(self.configuration(rules=(rule,)),clock=lambda:self.now)
  engine.ingest(self.event(metrics={'latency':999.0}));self.now+=timedelta(seconds=61)
  a=engine.ingest(self.event('e2'));self.assertNotEqual(self.status(a),'deviation');self.assertNotIn('latency',a.trends)

 def test_missing_expected_step_after_deadline(self):
  self.engine.ingest(self.event());self.now+=timedelta(seconds=11)
  a=self.engine.check('bank1','txn1',as_of=self.now)
  self.assertIn('finish',a.missing_expected_steps);self.assertNotEqual(self.status(a),'normal')

 def test_expected_step_completion_clears_missing(self):
  self.engine.ingest(self.event());self.now+=timedelta(seconds=5)
  self.engine.ingest(self.event('finish',step_id='finish'))
  self.now+=timedelta(seconds=6)
  self.assertNotIn('finish',self.engine.check('bank1','txn1',as_of=self.now).missing_expected_steps)

 def test_ttl_loss_is_explicit(self):
  engine=JourneyEngine(self.configuration(ttl_seconds=1,window_seconds=1),clock=lambda:self.now)
  engine.ingest(self.event());self.now+=timedelta(seconds=2)
  a=engine.ingest(self.event('new'))
  self.assertEqual(self.status(a),'insufficient_evidence');self.assertTrue(a.context_loss_reason)

 def test_event_and_trajectory_capacity_loss_is_explicit(self):
  engine=JourneyEngine(self.configuration(max_events=1,max_trajectories=1),clock=lambda:self.now)
  engine.ingest(self.event());self.now+=timedelta(seconds=1)
  a=engine.ingest(self.event('full'));self.assertTrue(a.context_loss_reason);self.assertEqual(self.status(a),'insufficient_evidence')
  engine.ingest(self.event('other',trajectory_id='txn2'))
  back=engine.ingest(self.event('back'));self.assertTrue(back.context_loss_reason);self.assertEqual(self.status(back),'insufficient_evidence')

 def test_naive_timestamps_nonfinite_metrics_and_unknown_step_rejected(self):
  for change in [{'event_time':self.now.replace(tzinfo=None)},{'ingested_at':self.now.replace(tzinfo=None)},{'metrics':{'latency':float('nan')}},{'metrics':{'latency':float('inf')}}]:
   with self.assertRaises(ValueError):self.event(**change)
  self.rejected_or_insufficient(lambda:self.engine.ingest(self.event(step_id='unknown')))

 def test_invalid_configuration_rejected(self):
  for change in [{'window_seconds':0},{'ttl_seconds':0},{'max_events':0},{'max_trajectories':0},{'max_lateness_seconds':-1},{'baseline':{}},{'baseline':{'latency':float('nan')}},{'rules':()}]:
   with self.subTest(change=change),self.assertRaises((ValueError,TypeError)):self.configuration(**change)

 def test_baseline_and_event_metrics_cannot_mutate_from_caller(self):
  baseline={'latency':100.0};config=self.configuration(baseline=baseline);baseline['latency']=999.0
  self.assertEqual(config.baseline['latency'],100.0)
  metrics={'latency':100.0};event=self.event(metrics=metrics);metrics['latency']=999.0
  self.assertEqual(event.metrics['latency'],100.0)

 def test_check_does_not_create_samples_or_future_evidence(self):
  self.engine.ingest(self.event());a=self.engine.check('bank1','txn1',as_of=self.now);b=self.engine.check('bank1','txn1',as_of=self.now)
  self.assertEqual(a.trends,b.trends);self.assertNotIn('latency',b.trends)

if __name__=='__main__':unittest.main()
