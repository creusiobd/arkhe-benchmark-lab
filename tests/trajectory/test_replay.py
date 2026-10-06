"""Replay and edge-case behavior, not production prediction claims."""
import contextlib,io,json,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from arkhe_trajectory import *
from arkhe_trajectory.cli import main

class ReplayTests(unittest.TestCase):
 def config(self):
  return JourneyConfig('t','j','1',(JourneyStep('sample'),),60,{'m':1},(ThresholdRule('r','m','gt',2),),ttl_seconds=120)
 def event(self,time=None,**changes):
  now=time or datetime.now(timezone.utc)-timedelta(seconds=5)
  data=dict(tenant_id='t',journey_id='j',journey_version='1',trajectory_id='r',event_id='a',step_id='sample',event_time=now,ingested_at=now,metrics={'m':1})
  data.update(changes);return TrajectoryEvent(**data)
 def invoke(self,args):
  out,err=io.StringIO(),io.StringIO()
  with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):code=main(args)
  return code,out.getvalue(),err.getvalue()
 def test_replay_validates_and_exports(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);config=root/'c.json';events=root/'e.jsonl';output=root/'o.jsonl'
   config.write_text(json.dumps(self.config().to_dict()));events.write_text(json.dumps(self.event().to_dict()))
   code,out,err=self.invoke(['replay',str(events),'--config',str(config),'--output',str(output)])
   self.assertEqual(code,0,err);self.assertEqual(json.loads(out)['status'],'normal')
   self.assertEqual(output.read_text(),out)
   self.assertEqual(self.invoke(['replay',str(events),'--config',str(config),'--output',str(events)])[0],2)
 def test_init_preset_valid_and_no_overwrite(self):
  with tempfile.TemporaryDirectory() as folder:
   target=Path(folder)/'journey.json'
   args=['init','--preset','cards','--tenant','my-bank','--output',str(target)]
   self.assertEqual(self.invoke(args)[0],0)
   self.assertEqual(JourneyConfig.from_dict(json.loads(target.read_text())).tenant_id,'my-bank')
   self.assertEqual(self.invoke(args)[0],2)
 def test_equal_timestamp_conflicting_latest_is_insufficient(self):
  now=datetime.now(timezone.utc);engine=JourneyEngine(self.config(),clock=lambda:now)
  engine.ingest(self.event(now));assessment=engine.ingest(self.event(now,event_id='b',metrics={'m':9}))
  self.assertEqual(assessment.status,'insufficient_evidence')
 def test_minimum_datetime_does_not_underflow_window(self):
  now=datetime(1,1,1,tzinfo=timezone.utc);engine=JourneyEngine(self.config(),clock=lambda:now)
  self.assertEqual(engine.ingest(self.event(now)).status,'normal')
 def test_terminal_successor_is_unexpected(self):
  now=datetime.now(timezone.utc);config=JourneyConfig('t','j','1',(JourneyStep('sample'),JourneyStep('other')),60,{'m':1},(ThresholdRule('r','m','gt',2),))
  engine=JourneyEngine(config,clock=lambda:now)
  engine.ingest(self.event(now-timedelta(seconds=1)))
  assessment=engine.ingest(self.event(now,event_id='b',step_id='other'))
  self.assertEqual(assessment.status,'deviation');self.assertEqual(assessment.findings[0].reason,'unexpected_transition')
 def test_stale_ingest_is_not_current_health(self):
  now=datetime.now(timezone.utc);engine=JourneyEngine(self.config(),clock=lambda:now)
  assessment=engine.ingest(self.event(now-timedelta(days=1)))
  self.assertEqual(assessment.status,'insufficient_evidence')
  self.assertIn('telemetry_stale',assessment.missing_metrics)
  self.assertEqual(assessment.window_end,now-timedelta(days=1))
 def test_schema_and_extreme_duration_rejected(self):
  with self.assertRaises(ValueError):self.event(schema_version='2')
  data=self.config().to_dict();data['schema_version']='2'
  with self.assertRaises(ValueError):JourneyConfig.from_dict(data)
  data['schema_version']='1';data['window_seconds']=1e300
  with self.assertRaises(ValueError):JourneyConfig.from_dict(data)
 def test_deadline_waits_for_lateness_allowance(self):
  now=datetime.now(timezone.utc);clock=[now]
  config=JourneyConfig('t','j','1',(JourneyStep('sample',('done',),2),JourneyStep('done')),60,{'m':1},(ThresholdRule('r','m','gt',2),),max_lateness_seconds=5)
  engine=JourneyEngine(config,clock=lambda:clock[0]);engine.ingest(self.event(now))
  clock[0]=now+timedelta(seconds=4);self.assertFalse(engine.check('t','r').missing_expected_steps)
  clock[0]=now+timedelta(seconds=8);self.assertEqual(engine.check('t','r').missing_expected_steps,('done',))

if __name__=='__main__':unittest.main()
