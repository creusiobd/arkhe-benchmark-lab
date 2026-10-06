"""Additional invariants for configurable temporal observations."""
from datetime import datetime,timedelta,timezone
import io,json,tempfile,contextlib,unittest
from pathlib import Path
from arkhe_trajectory import *
from arkhe_trajectory.cli import main

class TemporalInvariants(unittest.TestCase):
 def setUp(self):
  self.now=datetime(2026,10,6,0,tzinfo=timezone.utc)
 def config(self,**kwargs):
  data=dict(tenant_id='t',journey_id='j',version='1',steps=(JourneyStep('sample'),),
   window_seconds=60,baseline={'metric':100},rules=(ThresholdRule('r','metric','gt',120),),
   ttl_seconds=120,max_events=10,max_trajectories=2,max_lateness_seconds=5)
  data.update(kwargs);return JourneyConfig(**data)
 def event(self,n,value=100,**kwargs):
  data=dict(tenant_id='t',journey_id='j',journey_version='1',trajectory_id='r',event_id=str(n),
   step_id='sample',event_time=self.now,ingested_at=self.now,metrics={'metric':value})
  data.update(kwargs);return TrajectoryEvent(**data)
 def engine(self,config=None):return JourneyEngine(config or self.config(),clock=lambda:self.now)
 def test_serialization_strict_and_roundtrip(self):
  c=self.config();self.assertEqual(JourneyConfig.from_dict(c.to_dict()).configuration_hash,c.configuration_hash)
  e=self.event(1);self.assertEqual(TrajectoryEvent.from_dict(e.to_dict()),e)
  with self.assertRaises(ValueError):JourneyConfig.from_dict({**c.to_dict(),'typo':1})
  with self.assertRaises(ValueError):TrajectoryEvent.from_dict({**e.to_dict(),'ground_truth':True})
 def test_relative_and_delta_baseline_affect_decision(self):
  for reference,threshold in [('relative',0.2),('delta',20)]:
   engine=self.engine(self.config(rules=(ThresholdRule('r','metric','gt',threshold,reference=reference),)))
   a=engine.ingest(self.event(1,130));self.assertEqual(a.status,'deviation')
   self.assertEqual(a.findings[0].baseline,100)
   other=self.engine(self.config(baseline={'metric':200},rules=(ThresholdRule('r','metric','gt',threshold,reference=reference),)))
   self.assertEqual(other.ingest(self.event(1,130)).status,'normal')
 def test_zero_relative_baseline_rejected(self):
  with self.assertRaises(ValueError):self.config(baseline={'metric':0},rules=(ThresholdRule('r','metric','gt',1,reference='relative'),))
 def test_persistence_counts_samples_not_calls(self):
  engine=self.engine(self.config(rules=(ThresholdRule('r','metric','gt',120,persistence=2),)))
  event=self.event(1,130);self.assertEqual(engine.ingest(event).status,'normal')
  for _ in range(5):self.assertEqual(engine.check('t','r').status,'normal');self.assertEqual(engine.ingest(event).status,'normal')
  self.now+=timedelta(seconds=1);self.assertEqual(engine.ingest(self.event(2,130)).status,'deviation')
 def test_slope_warmup_and_persistence(self):
  engine=self.engine(self.config(rules=(ThresholdRule('r','metric','gt',1,aggregation='slope',min_samples=3,persistence=2),)))
  self.assertEqual(engine.ingest(self.event(1,100)).status,'insufficient_evidence')
  for n in range(2,5):
   self.now+=timedelta(seconds=10);assessment=engine.ingest(self.event(n,100+n*20))
  self.assertEqual(assessment.status,'deviation');self.assertGreater(assessment.findings[0].observed,1)
 def test_equal_timestamp_cannot_prove_slope(self):
  engine=self.engine(self.config(rules=(ThresholdRule('r','metric','gt',1,aggregation='slope',min_samples=2),)))
  engine.ingest(self.event(1));self.assertEqual(engine.ingest(self.event(2,200)).status,'insufficient_evidence')
 def test_accepted_late_event_uses_watermark_and_sorted_time(self):
  engine=self.engine(self.config(rules=(ThresholdRule('r','metric','gt',150,aggregation='mean'),)))
  engine.ingest(self.event(1,100));self.now+=timedelta(seconds=4)
  engine.ingest(self.event(2,140))
  late=self.event(3,120,event_time=self.now-timedelta(seconds=2))
  result=engine.ingest(late);self.assertAlmostEqual(result.trends['metric'],10);self.assertEqual(result.status,'normal')
 def test_historical_check_excludes_future_knowledge(self):
  start=self.now;engine=self.engine();engine.ingest(self.event(1,100));self.now+=timedelta(seconds=10)
  engine.ingest(self.event(2,999));self.assertEqual(engine.check('t','r',as_of=start).status,'normal')
 def test_tombstone_overflow_bounded_and_conservative(self):
  engine=self.engine(self.config(max_trajectories=1))
  for i in range(4):engine.ingest(self.event(i,trajectory_id=str(i)))
  stats=engine.state.stats();self.assertLessEqual(stats['tombstones'],1)
  self.assertTrue(stats['loss_registry_overflow'])
  self.assertEqual(engine.ingest(self.event(5,trajectory_id='new')).status,'insufficient_evidence')
 def test_nested_mutation_and_control_ids_rejected(self):
  event=self.event(1)
  with self.assertRaises(TypeError):event.metrics['metric']=999
  with self.assertRaises(ValueError):self.event(2,event_id='nul\x00')
 def test_mapping_adapter_and_missing_mapping(self):
  payload={'source':self.event(1).to_dict(),'signals':{'latency':100}}
  mapping={name:'source.'+name for name in ('tenant_id','journey_id','journey_version','trajectory_id','event_id','step_id','event_time','ingested_at')}
  adapted=MappingAdapter(mapping,{'metric':'signals.latency'}).adapt(payload)
  self.assertEqual(adapted.metrics['metric'],100)
  with self.assertRaises(ValueError):MappingAdapter(mapping,{'metric':'signals.absent'}).adapt(payload)
 def test_payload_bound(self):
  engine=self.engine(self.config(max_payload_bytes=20))
  with self.assertRaises(ValueError):engine.ingest(self.event(1))
 def test_clock_backward_and_future_check(self):
  engine=self.engine();engine.ingest(self.event(1))
  with self.assertRaises(ValueError):engine.check('t','r',as_of=self.now+timedelta(seconds=1))
  self.now-=timedelta(seconds=1)
  with self.assertRaises(ValueError):engine.check('t','r')
 def test_version_hash_changes(self):
  self.assertNotEqual(self.config().configuration_hash,self.config(version='2').configuration_hash)
 def test_all_profiles_validate(self):
  for name in ('cards','infrastructure','fulfillment'):
   profile=JourneyConfig.from_dict(json.loads(Path('configs/journeys',name+'.json').read_text()))
   self.assertTrue(profile.configuration_hash)
 def test_cli_validation_and_sensitive_json_failure(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'config.json';path.write_text('{"secret":"hidden-financial-data",BROKEN')
   error=io.StringIO()
   with contextlib.redirect_stderr(error):code=main(['validate-config',str(path)])
   self.assertEqual(code,2);self.assertNotIn('hidden-financial-data',error.getvalue())

if __name__=='__main__':unittest.main()
