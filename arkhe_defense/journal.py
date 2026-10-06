"""Host-owned SQLite observation ledger; serial single-tenant session.

Persists sanitized event summaries and trusted contexts in plaintext. The host
must secure the directory and retain every policy version needed for replay.
No external tool execution or exactly-once delivery is provided.
"""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from .config import SDKConfig
from .contracts import RuntimeContext, parse_event, utc_datetime
from .errors import DefenseError
from .evaluator import DefenseEvaluator


class JournalError(DefenseError):
    pass


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False)


class _ReplayProvider:
    def __init__(self, policy):
        self.policy = policy

    def get_active(self, tenant):
        if self.policy is None or self.policy.tenant_id != tenant:
            raise JournalError('historical policy unavailable')
        return self.policy


class DurableDefenseSession:
    """Exclusive process-local session with committed replayable observations.

    Commit or evaluation errors taint/close the session because in-memory state
    cannot be rolled back. Reopening reconstructs only committed observations.
    Ledger exhaustion fails closed; rows are never automatically evicted.
    """
    def __init__(self, provider, config, db_path, tenant, clock=None, max_rows=100000):
        if not isinstance(tenant, str) or not tenant.strip():
            raise JournalError('tenant required')
        if type(max_rows) is not int or max_rows < 1:
            raise JournalError('max_rows must be positive integer')
        self.provider = provider
        source_config = config or SDKConfig()
        self.config = SDKConfig.model_validate(source_config.model_dump(mode='python') if isinstance(source_config,SDKConfig) else source_config)
        self.tenant = tenant
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.max_rows = max_rows
        self.closed = False
        self.tainted = False
        self._db = self._lock = None
        path = Path(db_path).resolve()
        self._receipt = None
        try:
            # A separate SQLite transaction holds the ownership lock while the
            # ledger connection can durably commit individual observations.
            self._lock = sqlite3.connect(str(path) + '.lock', timeout=0)
            self._lock.execute('CREATE TABLE IF NOT EXISTS ownership (id INTEGER)')
            self._lock.commit()
            self._lock.execute('BEGIN IMMEDIATE')
            self._db = sqlite3.connect(str(path), timeout=0)
            self._db.execute('PRAGMA synchronous=FULL')
            self._db.execute('CREATE TABLE IF NOT EXISTS metadata (id INTEGER PRIMARY KEY, value TEXT NOT NULL)')
            self._db.execute('CREATE TABLE IF NOT EXISTS ledger (seq INTEGER PRIMARY KEY, receipt TEXT NOT NULL, event TEXT NOT NULL, context TEXT NOT NULL, policy_version TEXT, policy_hash TEXT, decision TEXT NOT NULL)')
            self._db.execute('CREATE TABLE IF NOT EXISTS integrity(id INTEGER PRIMARY KEY, tail TEXT NOT NULL, count INTEGER NOT NULL)')
            self._db.execute('CREATE TABLE IF NOT EXISTS digests(seq INTEGER PRIMARY KEY, digest TEXT NOT NULL)')
            fingerprint = hashlib.sha256(_json(self.config.model_dump(mode='json')).encode()).hexdigest()
            metadata = _json({'schema':1, 'tenant':tenant, 'config':fingerprint, 'max_rows':max_rows})
            row = self._db.execute('SELECT value FROM metadata WHERE id=1').fetchone()
            if not row and self._db.execute('SELECT COUNT(*) FROM ledger').fetchone()[0]:
                raise JournalError('journal tenant/configuration header missing')
            if row and row[0] != metadata:
                raise JournalError('journal tenant/configuration binding mismatch')
            self._db.execute('INSERT OR IGNORE INTO metadata VALUES (1,?)',(metadata,))
            count = self._db.execute('SELECT COUNT(*) FROM ledger').fetchone()[0]
            header = self._db.execute('SELECT tail,count FROM integrity WHERE id=1').fetchone()
            if header is None and count:
                raise JournalError('journal integrity header missing')
            self._tail = '0'*64
            self._db.execute('INSERT OR IGNORE INTO integrity VALUES(1,?,0)',(self._tail,))
            header = header or (self._tail,0)
            if count != header[1]:
                raise JournalError('journal count mismatch')
            self._db.commit()
            replay_provider = _ReplayProvider(None)
            self.engine = DefenseEvaluator(replay_provider,self.config,clock=lambda:self._receipt)
            if count > max_rows:
                raise JournalError('journal exceeds configured capacity')
            previous = None
            for seq in range(1,count+1):
                record = self._db.execute('SELECT receipt,event,context,policy_version,policy_hash,decision FROM ledger WHERE seq=?',(seq,)).fetchone()
                if record is None:
                    raise JournalError('journal sequence mismatch')
                receipt,event,context,version,digest,decision = record
                stored = self._db.execute('SELECT digest FROM digests WHERE seq=?',(seq,)).fetchone()
                computed = hashlib.sha256((self._tail+'\n'+_json([receipt,event,context,version,digest,decision])).encode()).hexdigest()
                if not stored or stored[0] != computed:
                    raise JournalError('journal chain mismatch')
                self._tail = computed
                self._count = seq
                self._receipt = utc_datetime(receipt)
                if previous is not None and self._receipt < previous:
                    raise JournalError('journal receipt clock regression')
                previous = self._receipt
                if version is None:
                    raise JournalError('historical policy missing')
                policy = provider.get(tenant,version)
                if policy.policy_hash != digest:
                    raise JournalError('historical policy hash mismatch')
                replay_provider.policy = policy
                observed = self.engine.ingest(json.loads(event),json.loads(context))
                if _json(observed.model_dump(mode='json')) != decision:
                    raise JournalError('journal replay decision mismatch')
            if self._tail != header[0]:
                raise JournalError('journal tail mismatch')
            self._count = count
            self._last_receipt = previous
            self.engine.policy_provider = provider
        except Exception as exc:
            self.close()
            if isinstance(exc,JournalError):
                raise
            raise JournalError('journal initialization/recovery failed') from exc

    def ingest(self,event,context):
        if self.closed or self.tainted:
            raise JournalError('journal session closed or tainted')
        event = parse_event(event)
        context = RuntimeContext.model_validate(context)
        if event.tenant_id != self.tenant or context.tenant_id != self.tenant:
            raise JournalError('journal tenant mismatch')
        self._receipt = utc_datetime(self.clock())
        if self._last_receipt and self._receipt < self._last_receipt:
            raise JournalError('host receipt clock regression')
        # These paths never mutate evaluator state and are deliberately not
        # persisted, so untrusted/future observations cannot poison recovery.
        if not self.engine._trusted(event,context) or event.occurred_at > self._receipt or event.ingested_at > self._receipt:
            return self.engine.ingest(event,context)
        try:
            policy = self.provider.get_active(self.tenant)
            if policy.tenant_id != self.tenant:
                raise JournalError('active policy tenant mismatch')
            count = self._db.execute('SELECT COUNT(*) FROM ledger').fetchone()[0]
            if count >= self.max_rows:
                raise JournalError('journal capacity exhausted')
            self._db.execute('BEGIN IMMEDIATE')
            self.engine.policy_provider = _ReplayProvider(policy)
            decision = self.engine.ingest(event,context)
            values = (self._receipt.isoformat(),_json(event.model_dump(mode='json')),
                 _json(context.model_dump(mode='json')),policy.version,policy.policy_hash,
                 _json(decision.model_dump(mode='json')))
            self._db.execute('INSERT INTO ledger(seq,receipt,event,context,policy_version,policy_hash,decision) VALUES (?,?,?,?,?,?,?)', (count+1,)+values)
            tail = hashlib.sha256((self._tail+'\n'+_json(list(values))).encode()).hexdigest()
            self._db.execute('INSERT INTO digests VALUES(?,?)',(count+1,tail))
            self._db.execute('UPDATE integrity SET tail=?,count=? WHERE id=1',(tail,count+1))
            self._db.commit()
            self._tail = tail
            self.engine.policy_provider = self.provider
            self._last_receipt = self._receipt
            return decision
        except Exception as exc:
            self.tainted = True
            if self._db:
                self._db.rollback()
            self.close()
            if isinstance(exc,JournalError):
                raise
            raise JournalError('journal append failed; session tainted') from exc

    def close(self):
        self.closed = True
        if self._db:
            self._db.close()
            self._db = None
        if self._lock:
            self._lock.rollback()
            self._lock.close()
            self._lock = None

    def __enter__(self):
        return self

    def __exit__(self,*args):
        self.close()
