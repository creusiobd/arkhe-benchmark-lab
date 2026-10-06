"""SQLite recovery invariants, not an external tool exactly-once claim."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from datetime import timedelta
from arkhe_defense.journal import DurableDefenseSession, JournalError
from arkhe_defense.config import SDKConfig
from tests.defense import test_security


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_security.DefenseSecurityTests()
        self.fixture.setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)/'journal.sqlite'
        self.sessions = []

    def tearDown(self):
        for session in self.sessions:
            session.close()
        self.tmp.cleanup()

    def open(self, **kwargs):
        f = self.fixture
        session = DurableDefenseSession(f.provider,SDKConfig(),self.path,'t1',clock=lambda:f.now,**kwargs)
        self.sessions.append(session)
        return session

    def test_recovery_same_decision(self):
        f = self.fixture
        session = self.open()
        original = session.ingest(f.propose(),f.agent)
        session.close()
        restored = self.open()
        self.assertEqual(restored.ingest(f.propose(),f.agent),original)

    def test_exclusive_open(self):
        self.open()
        with self.assertRaises(JournalError):
            self.open()

    def test_rejected_context_and_future_not_persisted(self):
        f = self.fixture
        session = self.open()
        bad = f.context('agent','agent1','agent',set())
        session.ingest(f.propose(),bad)
        session.ingest(f.propose(occurred_at=f.now+timedelta(seconds=1)),f.agent)
        self.assertEqual(session._db.execute('SELECT COUNT(*) FROM ledger').fetchone()[0],0)
        self.assertEqual(f.status(session.ingest(f.propose(),f.agent)),'approval_required')

    def test_capacity_failclosed(self):
        f = self.fixture
        session = self.open(max_rows=1)
        session.ingest(f.propose(),f.agent)
        with self.assertRaises(JournalError):
            session.ingest(f.propose('p2'),f.agent)
        self.assertTrue(session.closed)
        self.assertTrue(session.tainted)

    def test_tenant_binding(self):
        self.open().close()
        with self.assertRaises(JournalError):
            DurableDefenseSession(self.fixture.provider,SDKConfig(),self.path,'other')

    def test_decision_tampering_fails_recovery(self):
        f = self.fixture
        s = self.open()
        s.ingest(f.propose(),f.agent)
        s.close()
        db = sqlite3.connect(self.path)
        try:
            db.execute("UPDATE ledger SET decision='{}'")
            db.commit()
        finally:
            db.close()
        with self.assertRaises(JournalError):
            self.open()

    def test_missing_policy_fails_recovery(self):
        f = self.fixture
        s = self.open()
        s.ingest(f.propose(),f.agent)
        s.close()
        f.provider._snapshots.clear()
        with self.assertRaises(JournalError):
            self.open()

    def test_tail_deletion_fails_recovery(self):
        f = self.fixture
        s = self.open()
        s.ingest(f.propose(),f.agent)
        s.close()
        db = sqlite3.connect(self.path)
        try:
            db.execute('DELETE FROM ledger')
            db.commit()
        finally:
            db.close()
        with self.assertRaises(JournalError):
            self.open()

    def test_metadata_deletion_does_not_allow_rebinding(self):
        f = self.fixture
        s = self.open()
        s.ingest(f.propose(),f.agent)
        s.close()
        db = sqlite3.connect(self.path)
        try:
            db.execute('DELETE FROM metadata')
            db.commit()
        finally:
            db.close()
        with self.assertRaises(JournalError):
            self.open()

    def test_policy_switch_duplicate_and_ttl_replay(self):
        f = self.fixture
        s = self.open()
        p = f.propose()
        original = s.ingest(p,f.agent)
        f.provider.register(f.snapshot(version='v2',approval=False),f.admin,activate=True)
        self.assertEqual(s.ingest(p,f.agent),original)
        f.now += timedelta(seconds=1801)
        result = s.ingest(f.propose('p2',policy_version='v2'),f.agent)
        self.assertEqual(result.context_loss_reason,'ttl_expired')
        s.close()
        restored = self.open()
        self.assertEqual(restored.ingest(f.propose('p2',policy_version='v2'),f.agent),result)

    def test_expired_approval_not_resurrected(self):
        f = self.fixture
        s = self.open()
        proposal = f.propose()
        s.ingest(proposal,f.agent)
        s.ingest(f.approval(proposal),f.approver)
        s.close()
        f.now += timedelta(minutes=6)
        restored = self.open()
        decision = restored.ingest(f.completed(proposal),f.executor)
        self.assertEqual(f.status(decision),'policy_violation')

    def test_commit_failure_closes_session(self):
        f = self.fixture
        s = self.open()
        s._db.execute('PRAGMA query_only=ON')
        with self.assertRaises(JournalError):
            s.ingest(f.propose(),f.agent)
        self.assertTrue(s.tainted)
        with self.assertRaises(JournalError):
            s.ingest(f.propose(),f.agent)
        self.assertEqual(self.open()._db.execute('SELECT COUNT(*) FROM ledger').fetchone()[0],0)
