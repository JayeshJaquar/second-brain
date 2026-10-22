import base64
import hashlib
import io
import json
import math
import os
import secrets
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from PIL import Image
from .ingestion import clean, digest, units, OVERRIDES


class Store:
    def __init__(self, root: Path):
        self.root = Path(root); self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.root, 0o700)
        self.attachments = self.root / 'attachments'; self.attachments.mkdir(exist_ok=True, mode=0o700)
        self.lock = threading.RLock(); self.generation = 0
        self.db = sqlite3.connect(self.root / 'brain.sqlite3', check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        version=self.db.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0,1,2): raise ValueError('Unsupported database schema; use a compatible app version.')
        self.db.execute('PRAGMA foreign_keys=ON'); self.db.execute('PRAGMA journal_mode=DELETE')
        self.db.execute('PRAGMA secure_delete=ON')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS memories(
          id TEXT PRIMARY KEY,title TEXT NOT NULL,source TEXT NOT NULL,created_at REAL NOT NULL,
          published_at TEXT,raw_text TEXT NOT NULL,text TEXT NOT NULL,kind TEXT NOT NULL,
          image TEXT,ocr_json TEXT NOT NULL,hash TEXT UNIQUE NOT NULL,screened INTEGER NOT NULL,
          topic TEXT NOT NULL DEFAULT 'unclassified');
        CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY,memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
          start INTEGER NOT NULL,end INTEGER NOT NULL,text TEXT NOT NULL);
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(id UNINDEXED,text,tokenize='unicode61');
        CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN DELETE FROM chunks_fts WHERE id=old.id; END;
        CREATE TABLE IF NOT EXISTS embeddings(chunk_id TEXT REFERENCES chunks(id) ON DELETE CASCADE,
          model TEXT NOT NULL,vector BLOB NOT NULL,PRIMARY KEY(chunk_id,model));
        CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY,memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
          prompt TEXT NOT NULL,answer TEXT NOT NULL,due REAL NOT NULL,interval REAL NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,review_id TEXT NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
          at REAL NOT NULL,correct INTEGER NOT NULL,hints INTEGER NOT NULL,elapsed REAL NOT NULL,prior INTEGER NOT NULL,previous_accuracy REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS vision(memory_id TEXT PRIMARY KEY REFERENCES memories(id) ON DELETE CASCADE,
          model TEXT NOT NULL,description TEXT NOT NULL,at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS traces(id TEXT PRIMARY KEY,at REAL NOT NULL,data TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS chunks_memory ON chunks(memory_id);
        ''')
        # Additive migration keeps existing memories and practice history intact.
        columns={row[1] for row in self.db.execute('PRAGMA table_info(memories)')}
        if 'extraction_json' not in columns:
            self.db.execute("ALTER TABLE memories ADD COLUMN extraction_json TEXT NOT NULL DEFAULT '{}'")
        event_columns={row[1] for row in self.db.execute('PRAGMA table_info(events)')}
        for name in ['response','correction']:
            if name not in event_columns:
                self.db.execute(f"ALTER TABLE events ADD COLUMN {name} TEXT NOT NULL DEFAULT ''")
        self.db.execute("INSERT OR REPLACE INTO meta VALUES('schema_version','2')")
        self.db.execute('PRAGMA user_version=2'); self.db.commit()
        os.chmod(self.root / 'brain.sqlite3', 0o600)
        tokenfile = self.root / 'backend.token'
        if not tokenfile.exists():
            fd = os.open(tokenfile, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as f: f.write(secrets.token_urlsafe(32))
        os.chmod(tokenfile, 0o600); self.token = tokenfile.read_text().strip()

    def rows(self, sql, args=()):
        with self.lock: return [dict(r) for r in self.db.execute(sql, args)]

    def add(self, *, title, source, text, image=None, kind='note', published_at=None, ocr=None, id=None, created_at=None, raw_text=None, extraction=None):
        if not text.strip() and not image: raise ValueError('A memory needs text or an image.')
        image_hash = None; created_file = False
        if image:
            if len(image) > 20_000_000: raise ValueError('Image must be smaller than 20 MB.')
            with Image.open(io.BytesIO(image)) as im:
                if im.format != 'PNG' or im.width * im.height > 20_000_000: raise ValueError('Use a PNG smaller than 20 megapixels.')
                im.verify()
            image_hash = hashlib.sha256(image).hexdigest() + '.png'
        text_clean = clean(text, kind)
        fingerprint = digest(source, text_clean, image_hash or '')
        with self.lock:
            old = self.rows('SELECT id FROM memories WHERE hash=?', (fingerprint,))
            if old: return self.memory(old[0]['id'])
            mid = str(uuid.UUID(id)) if id else str(uuid.uuid4())
            if image and not (self.attachments / image_hash).exists():
                fd = os.open(self.attachments / image_hash, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, 'wb') as f: f.write(image)
                created_file = True
            try:
                with self.db:
                    self.db.execute('INSERT INTO memories(id,title,source,created_at,published_at,raw_text,text,kind,image,ocr_json,hash,screened,extraction_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (mid,title,source,created_at if created_at is not None else time.time(),published_at,raw_text if raw_text is not None else text,text_clean,kind,image_hash,json.dumps(ocr or []),fingerprint,bool(OVERRIDES.search(text)),json.dumps(extraction or {})))
                    for start,end,part in units(text_clean):
                        cid = f'{mid}:{start}:{end}'
                        self.db.execute('INSERT INTO chunks VALUES(?,?,?,?,?)',(cid,mid,start,end,part))
                        self.db.execute('INSERT INTO chunks_fts VALUES(?,?)',(cid,part))
            except Exception:
                if created_file: (self.attachments / image_hash).unlink(missing_ok=True)
                raise
            self.generation += 1
            return self.memory(mid)

    def memory(self, mid):
        rows = self.rows('SELECT * FROM memories WHERE id=?',(mid,))
        if not rows: raise KeyError(mid)
        result = rows[0]; result['has_image'] = bool(result.pop('image'))
        result['ocr'] = json.loads(result.pop('ocr_json')); result.pop('hash')
        result['extraction'] = json.loads(result.pop('extraction_json'))
        return result

    def list(self):
        return self.rows('SELECT id,title,source,created_at,published_at,text,kind,(image IS NOT NULL) AS has_image,screened,topic FROM memories ORDER BY created_at DESC')

    def passage(self, mid, chunk_id):
        with self.lock:
            memory=self.memory(mid)
            rows=self.rows('SELECT * FROM chunks WHERE id=? AND memory_id=?',(chunk_id,mid))
            if not rows: raise KeyError(chunk_id)
            chunk=rows[0]; start,end=chunk['start'],chunk['end']; text=memory['text']
            if text[start:end]!=chunk['text']: raise ValueError('Stored passage no longer matches its source.')
        regions=[]; cursor=0
        # Native OCR is ordered and joined with newlines. Map only exact surviving text.
        # A region covers a recognized line, not necessarily the precise glyphs of a quote.
        for region in memory['ocr']:
            value=region.get('text')
            if not isinstance(value,str) or not value: continue
            pos=text.find(value,cursor)
            if pos<0: continue
            cursor=pos+len(value)
            if cursor<=start or pos>=end: continue
            try:
                x,y,w,h=[float(region[k]) for k in ('x','y','width','height')]
                confidence=float(region['confidence'])
            except (KeyError,ValueError,TypeError): continue
            if not all(math.isfinite(v) for v in (x,y,w,h,confidence)): continue
            if not (0<=x<=1 and 0<=y<=1 and 0<w<=1 and 0<h<=1 and x+w<=1.000001 and y+h<=1.000001 and 0<=confidence<=1): continue
            regions.append(dict(text=value,x=x,top=max(0,1-y-h),width=w,height=h,confidence=confidence))
        return dict(chunk_id=chunk_id,memory_id=mid,start=start,end=end,
                    before=text[:start],highlight=text[start:end],after=text[end:],regions=regions,
                    coordinate_note='Boxes show exact-text-matched OCR lines, not verified diagram relationships.')

    def image_path(self, mid):
        rows = self.rows('SELECT image FROM memories WHERE id=?',(mid,))
        if not rows or not rows[0]['image']: raise KeyError(mid)
        return self.attachments / rows[0]['image']

    def delete(self, mid):
        with self.lock:
            self.memory(mid)
            image = self.rows('SELECT image FROM memories WHERE id=?',(mid,))[0]['image']
            with self.db:
                self.db.execute('DELETE FROM memories WHERE id=?',(mid,))
                # Conservative invalidation: traces may reference deleted source excerpts.
                self.db.execute('DELETE FROM traces')
            self.generation += 1
            if image and not self.rows('SELECT id FROM memories WHERE image=?',(image,)):
                (self.attachments / image).unlink(missing_ok=True)

    def migrate_legacy(self):
        path = self.root / 'memories.json'
        if not path.exists() or self.rows("SELECT value FROM meta WHERE key='legacy_import'"): return 0
        # Preserve the original file. Per-record validation and stable IDs allow retry after a partial import.
        data = json.loads(path.read_text()); count = 0
        for item in data:
            mid = str(uuid.UUID(item['id']))
            if self.rows('SELECT id FROM memories WHERE id=?',(mid,)): continue
            self.add(id=mid,title=item['title'],source=item['source'],text=item['text'],kind='legacy',
                image=base64.b64decode(item['screenshotPNG'],validate=True) if item.get('screenshotPNG') else None,
                created_at=item['createdAt']+978307200)
            count += 1
        with self.db: self.db.execute("INSERT INTO meta VALUES('legacy_import',?)",(str(time.time()),))
        return count

    def candidates(self, memory_id=None):
        return self.rows('SELECT c.*,m.title,m.source,m.created_at,m.published_at FROM chunks c JOIN memories m ON m.id=c.memory_id WHERE m.screened=0' + (' AND m.id=?' if memory_id else ''), (memory_id,) if memory_id else ())

    def keyword_candidates(self, tokens, memory_id=None, limit=30):
        """Quoted tokens cannot become FTS operators. FTS5 ranks lower scores first."""
        if not tokens: return []
        query=' OR '.join('"'+t.replace('"','""')+'"' for t in sorted(set(tokens))[:64])
        return self.rows(
            'SELECT c.*,m.title,m.source,m.created_at,m.published_at,-bm25(chunks_fts) AS score '
            'FROM chunks_fts JOIN chunks c ON c.id=chunks_fts.id JOIN memories m ON m.id=c.memory_id '
            'WHERE chunks_fts MATCH ? AND m.screened=0'+(' AND m.id=?' if memory_id else '')+
            ' ORDER BY bm25(chunks_fts),c.id LIMIT ?',
            (query,memory_id,limit) if memory_id else (query,limit))

    def save_review(self, mid, prompt, answer):
        memory = self.memory(mid)
        if memory['screened'] or answer not in memory['text']: raise ValueError('Review answer must be a verified source excerpt.')
        rid = str(uuid.uuid4())
        with self.lock, self.db: self.db.execute('INSERT INTO reviews(id,memory_id,prompt,answer,due) VALUES(?,?,?,?,?)',(rid,mid,prompt,answer,time.time()))
        return rid

    def record_review(self, rid, correct, hints, response="", correction=""):
        with self.lock:
            rows = self.rows('SELECT * FROM reviews WHERE id=?',(rid,))
            if not rows: raise KeyError(rid)
            review = rows[0]; events = self.rows('SELECT * FROM events WHERE review_id=? ORDER BY at',(rid,))
            now = time.time(); elapsed = (now-events[-1]['at'])/86400 if events else 0
            accuracy = sum(x['correct'] for x in events)/len(events) if events else .5
            # Conservative baseline: a hinted answer is not independent successful recall.
            independent = bool(correct and not hints)
            interval = min(90,review['interval']*2) if independent else 1
            with self.db:
                self.db.execute('INSERT INTO events(review_id,at,correct,hints,elapsed,prior,previous_accuracy,response,correction) VALUES(?,?,?,?,?,?,?,?,?)',
                    (rid,now,independent,hints,elapsed,len(events),accuracy,response,correction))
                self.db.execute('UPDATE reviews SET due=?,interval=? WHERE id=?',(now+interval*86400,interval,rid))
            return {'interval_days':interval,'independent_recall':independent}

    def trace(self, data):
        tid = str(uuid.uuid4())
        with self.lock, self.db: self.db.execute('INSERT INTO traces VALUES(?,?,?)',(tid,time.time(),json.dumps(data)))
        return tid
