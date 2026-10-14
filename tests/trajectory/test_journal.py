import json
import sqlite3
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from tests.trajectory import test_invariants
from arkhe_trajectory.journal import DurableJourneySession,JournalError
from arkhe_trajectory.errors import DuplicateEventError,EventRejectedError

class JourneyJournalTests(unittest.TestCase):
    def setUp(self):
        self.f=test_invariants.TemporalInvariants()
        self.f.setUp()
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'journey.sqlite'
        self.sessions=[]
    def tearDown(self):
        for s in self.sessions:s.close()
        self.tmp.cleanup()
    def open(self,config=None,**kwargs):
        s=DurableJourneySession(config or self.f.config(),self.path,clock=lambda:self.f.now,**kwargs)
        self.sessions.append(s)
        return s
    def mutate(self,sql):
        db=sqlite3.connect(self.path)
        try:db.execute(sql);db.commit()
        finally:db.close()
    def test_replay_ingest_duplicate_and_check(self):
        s=self.open()
        e=self.f.event(1)
        original=s.ingest(e)
        self.assertEqual(s.ingest(e),original)
        self.f.now+=timedelta(seconds=121)
        expired=s.check('t','r')
        s.close()
        restored=self.open()
        self.assertEqual(restored._count,3)
        self.assertEqual(restored.check('t','r').context_loss_reason,expired.context_loss_reason)
    def test_exclusive(self):
        self.open()
        with self.assertRaises(JournalError):self.open()
    def test_config_change_rejected(self):
        self.open().close()
        with self.assertRaises(JournalError):self.open(self.f.config(baseline={'metric':101}))
    def test_tail_deletion_rejected(self):
        s=self.open();s.ingest(self.f.event(1));s.close()
        self.mutate('DELETE FROM ledger')
        with self.assertRaises(JournalError):self.open()
    def test_row_tampering_rejected(self):
        s=self.open();s.ingest(self.f.event(1));s.close()
        self.mutate("UPDATE ledger SET record='{}'")
        with self.assertRaises(JournalError):self.open()
    def test_capacity_and_commit_failure_taint(self):
        s=self.open(max_rows=1);s.ingest(self.f.event(1))
        with self.assertRaises(JournalError):s.check('t','r')
        self.assertTrue(s.closed);self.assertTrue(s.tainted)
    def test_write_failure_reopen_no_uncommitted_state(self):
        s=self.open();s._db.execute('PRAGMA query_only=ON')
        with self.assertRaises(JournalError):s.ingest(self.f.event(1))
        self.assertTrue(s.tainted)
        self.assertEqual(self.open()._count,0)
    def test_wrong_tenant_refused_without_closing(self):
        s=self.open()
        with self.assertRaises(EventRejectedError):s.ingest(self.f.event(1,tenant_id='other'))
        self.assertFalse(s.closed or s.tainted)
        self.assertEqual(s.ingest(self.f.event(1)).status,'normal')
        self.assertEqual(s._count,1)
    def test_invalid_input_refused_without_closing_and_replays(self):
        s=self.open(self.f.config(max_payload_bytes=4096))
        first=s.ingest(self.f.event(1))
        refused=[lambda:s.ingest(self.f.event(9,journey_version='2')),
                 lambda:s.ingest(self.f.event(9,step_id='nope')),
                 lambda:s.ingest(self.f.event(9,event_time=self.f.now+timedelta(seconds=5),ingested_at=self.f.now+timedelta(seconds=5))),
                 lambda:s.ingest(self.f.event(9,dimensions={f'd{i}':'x'*1000 for i in range(30)})),
                 lambda:s.check('other','r'),
                 lambda:s.check('t','r',as_of=self.f.now+timedelta(seconds=5))]
        for attempt in refused:
            with self.assertRaises(EventRejectedError):attempt()
        with self.assertRaises(DuplicateEventError):s.ingest(self.f.event(1,555))
        self.assertFalse(s.closed or s.tainted)
        current=s.check('t','r')
        s.close()
        restored=self.open(self.f.config(max_payload_bytes=4096))
        self.assertEqual(restored._count,2)
        self.assertEqual(restored.ingest(self.f.event(1)),first)
        self.assertEqual(restored.check('t','r'),current)
    def test_clock_regression_after_refusal_still_closes(self):
        s=self.open()
        start=self.f.now
        self.f.now=start+timedelta(seconds=30)
        with self.assertRaises(EventRejectedError):s.ingest(self.f.event(1,step_id='nope'))
        self.f.now=start
        with self.assertRaises(JournalError):s.ingest(self.f.event(1))
        self.assertTrue(s.closed)
    def test_historical_check_replay_and_clock_regression(self):
        s=self.open()
        start=self.f.now
        s.ingest(self.f.event(1))
        self.f.now+=timedelta(seconds=10)
        s.ingest(self.f.event(2,999))
        historical=s.check('t','r',as_of=start)
        self.assertEqual(historical.status,'normal')
        s.close()
        restored=self.open()
        self.assertEqual(restored.check('t','r',as_of=start),historical)
        self.f.now=start
        with self.assertRaises(JournalError):restored.check('t','r')
        self.assertTrue(restored.closed)
