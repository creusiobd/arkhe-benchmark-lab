"""Host-owned plaintext SQLite ledger. Serial; no external exactly-once claim."""
import hashlib
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from .config import JourneyConfig
from .contracts import TrajectoryEvent, aware
from .engine import JourneyEngine
from .errors import TrajectoryError


class JournalError(TrajectoryError):
    pass


def encode(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)


def chain(previous,record):
    return hashlib.sha256((previous+'\n'+record).encode('utf-8')).hexdigest()


class DurableJourneySession:
    """Single-owner local observation journal bound to configuration hash.

    Every successful ingest/check (including duplicates) is replayed with its
    original host receipt time. Hash chain detects accidental mutation, not an
    attacker controlling storage. No automatic deletion or compaction.
    """
    def __init__(self,config,db_path,clock=None,max_rows=100000):
        self.config=JourneyConfig.from_dict(config.to_dict() if isinstance(config,JourneyConfig) else config)
        if type(max_rows) is not int or max_rows<1:
            raise JournalError('max_rows: positive integer required')
        self.max_rows=max_rows
        self.clock=clock or (lambda:datetime.now(timezone.utc))
        self.closed=False
        self.tainted=False
        self._db=self._lock=None
        self._receipt=None
        self._last_receipt=None
        self._tail='0'*64
        path=Path(db_path).resolve()
        try:
            self._lock=sqlite3.connect(str(path)+'.lock',timeout=0)
            self._lock.execute('CREATE TABLE IF NOT EXISTS ownership(id INTEGER)')
            self._lock.commit()
            self._lock.execute('BEGIN IMMEDIATE')
            self._db=sqlite3.connect(str(path),timeout=0)
            self._db.execute('PRAGMA synchronous=FULL')
            self._db.execute('CREATE TABLE IF NOT EXISTS metadata(id INTEGER PRIMARY KEY,value TEXT NOT NULL,tail TEXT NOT NULL,count INTEGER NOT NULL)')
            self._db.execute('CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY,record TEXT NOT NULL,digest TEXT NOT NULL)')
            binding=encode({'schema':1,'configuration_hash':self.config.configuration_hash,'max_rows':max_rows})
            header=self._db.execute('SELECT value,tail,count FROM metadata WHERE id=1').fetchone()
            if header and header[0]!=binding:
                raise JournalError('journal configuration binding mismatch')
            if not header:
                if self._db.execute('SELECT COUNT(*) FROM ledger').fetchone()[0]:
                    raise JournalError('journal header missing')
                self._db.execute('INSERT INTO metadata VALUES(1,?,?,0)',(binding,self._tail))
                self._db.commit()
                header=(binding,self._tail,0)
            count=self._db.execute('SELECT COUNT(*) FROM ledger').fetchone()[0]
            if count>max_rows or count!=header[2]:
                raise JournalError('journal count mismatch')
            self.engine=JourneyEngine(self.config,clock=lambda:self._receipt)
            for seq in range(1,count+1):
                row=self._db.execute('SELECT record,digest FROM ledger WHERE seq=?',(seq,)).fetchone()
                if row is None:
                    raise JournalError('journal sequence mismatch')
                record,digest=row
                if chain(self._tail,record)!=digest:
                    raise JournalError('journal chain mismatch')
                data=json.loads(record)
                self._receipt=aware(datetime.fromisoformat(data['receipt']),'receipt')
                if self._last_receipt and self._receipt<self._last_receipt:
                    raise JournalError('journal clock regression')
                observed=self._apply(data['kind'],data['payload'])
                if encode(observed.to_dict())!=encode(data['assessment']):
                    raise JournalError('journal replay assessment mismatch')
                self._last_receipt=self._receipt
                self._tail=digest
            if self._tail!=header[1]:
                raise JournalError('journal tail mismatch')
            self._count=count
        except Exception as exc:
            self.close()
            if isinstance(exc,JournalError):raise
            raise JournalError('journal initialization/recovery failed') from exc

    def _apply(self,kind,payload):
        if kind=='ingest':return self.engine.ingest(TrajectoryEvent.from_dict(payload))
        if kind=='check':
            as_of=datetime.fromisoformat(payload['as_of']) if payload['as_of'] is not None else None
            return self.engine.check(payload['tenant_id'],payload['trajectory_id'],as_of)
        raise JournalError('journal operation invalid')

    def _record(self,kind,payload):
        if self.closed or self.tainted:raise JournalError('journal closed or tainted')
        try:
            self._receipt=aware(self.clock(),'clock')
            if self._last_receipt and self._receipt<self._last_receipt:
                raise JournalError('host clock regression')
            if self._count>=self.max_rows:raise JournalError('journal capacity exhausted')
            self._db.execute('BEGIN IMMEDIATE')
            assessment=self._apply(kind,payload)
            record=encode({'receipt':self._receipt.isoformat(),'kind':kind,'payload':payload,'assessment':assessment.to_dict()})
            digest=chain(self._tail,record)
            self._db.execute('INSERT INTO ledger VALUES(?,?,?)',(self._count+1,record,digest))
            self._db.execute('UPDATE metadata SET tail=?,count=? WHERE id=1',(digest,self._count+1))
            self._db.commit()
            self._count+=1
            self._tail=digest
            self._last_receipt=self._receipt
            return assessment
        except Exception as exc:
            self.tainted=True
            if self._db:self._db.rollback()
            self.close()
            if isinstance(exc,JournalError):raise
            raise JournalError('journal append failed; session tainted') from exc

    def ingest(self,event):
        event=TrajectoryEvent.from_dict(event.to_dict() if isinstance(event,TrajectoryEvent) else event)
        return self._record('ingest',event.to_dict())

    def check(self,tenant_id,trajectory_id,as_of=None):
        return self._record('check',{'tenant_id':tenant_id,'trajectory_id':trajectory_id,'as_of':aware(as_of,'as_of').isoformat() if as_of is not None else None})

    def close(self):
        self.closed=True
        if self._db:self._db.close();self._db=None
        if self._lock:self._lock.rollback();self._lock.close();self._lock=None

    def __enter__(self):return self
    def __exit__(self,*args):self.close()
