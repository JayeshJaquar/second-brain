"""FTS5 keyword retrieval and cached vector search; document embeddings are built off the query path."""
import json
import math
import re
import threading
from collections import Counter
import numpy as np
from .config import MODELS

STOP = set('a an the is are was were be to of and or in on at for from by with as it this that i me my you your what which who how why when where do does did can could would should will please tell explain according about give answer saved memory memories article note notes'.split())

def terms(text): return [w for w in re.findall(r'\w+', text.lower()) if w not in STOP]

def lexical(question, rows):
    counts = [Counter(terms(row['text'])) for row in rows]; query = set(terms(question))
    lengths = [sum(c.values()) for c in counts]; avg = sum(lengths)/max(1,len(lengths)) or 1
    df = Counter(t for c in counts for t in c)
    scored = []
    for i,c in enumerate(counts):
        score = sum(math.log(1+(len(rows)-df[t]+.5)/(df[t]+.5))*c[t]*2.5/(c[t]+1.5*(.25+.75*lengths[i]/avg)) for t in query if c[t])
        if score: scored.append(dict(rows[i],score=score))
    return sorted(scored,key=lambda r:(-r['score'],r['id']))


class Retriever:
    def __init__(self, store, model_dir=MODELS):
        self.store=store; self.model_dir=model_dir; self.encoder=None; self.reranker=None
        self.lock=threading.RLock(); self.model_lock=threading.RLock()
        self.index_lock=threading.Lock(); self.wake=threading.Event(); self.stop=threading.Event()
        self.worker=None; self.index_revision=0; self.cache=None; self.index_error=None
        self.indexing=False

    def manifest(self):
        path=self.model_dir/'manifest.json'
        return json.loads(path.read_text()) if path.exists() else {}

    def model_key(self): return self.manifest().get('encoder',{}).get('revision','local')

    def available(self): return (self.model_dir/'encoder/config.json').exists()

    def load(self):
        with self.model_lock:
            if self.encoder is None:
                from sentence_transformers import SentenceTransformer
                self.encoder=SentenceTransformer(str(self.model_dir/'encoder'),local_files_only=True,trust_remote_code=False,device='cpu')
            return self.encoder

    def start(self):
        if self.worker is not None: return
        self.stop.clear()
        self.worker=threading.Thread(target=self._work,name='brain-index',daemon=True)
        self.worker.start(); self.request_index()

    def request_index(self): self.wake.set()

    def close(self):
        self.stop.set(); self.wake.set()
        if self.worker is not None: self.worker.join(); self.worker=None

    def _work(self):
        while not self.stop.is_set():
            self.wake.wait(); self.wake.clear()
            if self.stop.is_set(): break
            try: self.index_pending()
            except Exception as exc:
                # No source text in status; a new save/retry/restart can retry the batch.
                self.index_error=type(exc).__name__

    def index_pending(self, batch_size=16):
        """Encode small batches without holding the SQLite lock; usable by offline experiments too."""
        if not self.available(): return 0
        total=0; key=self.model_key()
        with self.index_lock:
            self.indexing=True; self.index_error=None
            try:
                while not self.stop.is_set():
                    missing=self.store.rows(
                        'SELECT c.id,c.text FROM chunks c JOIN memories m ON m.id=c.memory_id '
                        'LEFT JOIN embeddings e ON e.chunk_id=c.id AND e.model=? '
                        'WHERE e.chunk_id IS NULL AND m.screened=0 ORDER BY c.id LIMIT ?', (key,batch_size))
                    if not missing: break
                    with self.model_lock:
                        matrix=self.load().encode([r['text'] for r in missing],normalize_embeddings=True,show_progress_bar=False)
                    with self.store.lock, self.store.db:
                        for row,vec in zip(missing,matrix):
                            # A deletion during encoding must not resurrect its vector.
                            self.store.db.execute(
                                'INSERT OR IGNORE INTO embeddings SELECT c.id,?,? FROM chunks c '
                                'JOIN memories m ON m.id=c.memory_id WHERE c.id=? AND m.screened=0',
                                (key,np.asarray(vec,dtype=np.float32).tobytes(),row['id']))
                        self.index_revision+=1
                    total+=len(missing)
            finally: self.indexing=False
        return total

    def status(self):
        counts=self.store.rows(
            'SELECT count(*) AS total,count(e.chunk_id) AS indexed FROM chunks c '
            'JOIN memories m ON m.id=c.memory_id LEFT JOIN embeddings e ON e.chunk_id=c.id AND e.model=? '
            'WHERE m.screened=0',(self.model_key(),))[0]
        return dict(counts,pending=counts['total']-counts['indexed'],running=self.indexing,
                    available=self.available(),error=self.index_error)

    def _snapshot(self):
        # Search lock protects the cache. Only short reads happen under the database lock.
        with self.store.lock:
            key=(self.store.generation,self.index_revision,self.model_key())
            if self.cache is not None and self.cache[0]==key: return self.cache
            rows=self.store.candidates()
            vectors={r['chunk_id']:r['vector'] for r in self.store.rows('SELECT * FROM embeddings WHERE model=?',(key[2],))}
        indexed=[r for r in rows if r['id'] in vectors]
        matrix=np.stack([np.frombuffer(vectors[r['id']],dtype=np.float32) for r in indexed]) if indexed else None
        self.cache=(key,rows,indexed,matrix)
        return self.cache

    def search(self, question, mode='hybrid', memory_id=None, limit=8):
        if mode not in {'lexical','dense','hybrid','rerank'}: raise ValueError('Unknown retrieval mode')
        with self.lock:
            warnings=[]; actual=mode
            with self.store.lock:
                generation=self.store.generation
                sparse=self.store.keyword_candidates(terms(question),memory_id,max(30,limit))
            if mode=='lexical': return sparse[:limit],warnings,actual
            if not self.available():
                return sparse[:limit],['Semantic model unavailable; using keyword search.'],'lexical'
            _,rows,indexed,matrix=self._snapshot()
            scoped=[r for r in rows if memory_id is None or r['memory_id']==memory_id]
            positions=[i for i,r in enumerate(indexed) if memory_id is None or r['memory_id']==memory_id]
            if len(positions)<len(scoped):
                warnings.append('Some passages are still being indexed; semantic results may be incomplete. Keyword search includes newly saved text.')
                self.request_index()
            if not positions:
                return sparse[:limit],warnings+['No indexed semantic passages; using keyword search.'],'lexical'
            with self.model_lock:
                q=self.load().encode([question],normalize_embeddings=True,show_progress_bar=False)[0]
            scores=matrix[positions]@q
            ranked=sorted(range(len(positions)),key=lambda i:(-float(scores[i]),indexed[positions[i]]['id']))[:max(30,limit)]
            dense=[dict(indexed[positions[i]],score=float(scores[i])) for i in ranked]
            if mode=='dense': result=dense
            else:
                fused_scores=Counter(); mapping={r['id']:r for r in sparse+dense}
                for ranked_rows in [sparse[:30],dense[:30]]:
                    for rank,row in enumerate(ranked_rows): fused_scores[row['id']]+=1/(60+rank+1)
                result=[dict(mapping[mid],score=score) for mid,score in sorted(fused_scores.items(),key=lambda x:(-x[1],x[0]))]
                if mode=='rerank' and result:
                    if not (self.model_dir/'reranker/config.json').exists():
                        warnings.append('Reranker unavailable; using hybrid retrieval.'); actual='hybrid'
                    else:
                        with self.model_lock:
                            if self.reranker is None:
                                from sentence_transformers import CrossEncoder
                                self.reranker=CrossEncoder(str(self.model_dir/'reranker'),local_files_only=True,trust_remote_code=False,device='cpu')
                            top=result[:max(20,limit)]
                            values=self.reranker.predict([(question,r['text']) for r in top],show_progress_bar=False)
                        result=sorted([dict(r,score=float(v)) for r,v in zip(top,values)],key=lambda r:(-r['score'],r['id']))
            if self.store.generation!=generation:
                return [],warnings+['Memories changed during retrieval; please retry.'],actual
            return result[:limit],warnings,actual
