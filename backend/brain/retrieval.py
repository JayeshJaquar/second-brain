"""Lexical, dense, hybrid and reranked retrieval over identical sentence spans."""
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
        self.store=store; self.model_dir=model_dir; self.encoder=None; self.reranker=None; self.lock=threading.RLock()

    def manifest(self):
        path=self.model_dir/'manifest.json'
        return json.loads(path.read_text()) if path.exists() else {}

    def load(self):
        if self.encoder is None:
            from sentence_transformers import SentenceTransformer
            self.encoder=SentenceTransformer(str(self.model_dir/'encoder'),local_files_only=True,trust_remote_code=False,device='cpu')
        return self.encoder

    def dense(self, question, rows):
        if not rows: return []
        encoder=self.load(); key=self.manifest().get('encoder',{}).get('revision','local')
        vectors={r['chunk_id']:np.frombuffer(r['vector'],dtype=np.float32) for r in self.store.rows('SELECT * FROM embeddings WHERE model=?',(key,))}
        missing=[r for r in rows if r['id'] not in vectors]
        if missing:
            matrix=encoder.encode([r['text'] for r in missing],normalize_embeddings=True,show_progress_bar=False)
            with self.store.lock, self.store.db:
                for row,vec in zip(missing,matrix):
                    vectors[row['id']]=np.asarray(vec,dtype=np.float32)
                    self.store.db.execute('INSERT OR REPLACE INTO embeddings VALUES(?,?,?)',(row['id'],key,vectors[row['id']].tobytes()))
        q=encoder.encode([question],normalize_embeddings=True,show_progress_bar=False)[0]
        return sorted([dict(r,score=float(vectors[r['id']]@q)) for r in rows],key=lambda r:(-r['score'],r['id']))

    def search(self, question, mode='hybrid', memory_id=None, limit=8):
        if mode not in {'lexical','dense','hybrid','rerank'}: raise ValueError('Unknown retrieval mode')
        with self.lock, self.store.lock:
            rows=self.store.candidates(memory_id); warnings=[]; actual=mode
            sparse=lexical(question,rows)
            if mode=='lexical': return sparse[:limit],warnings,actual
            if not (self.model_dir/'encoder/config.json').exists():
                return sparse[:limit],['Semantic model unavailable; using keyword search.'],'lexical'
            dense=self.dense(question,rows)
            if mode=='dense': return dense[:limit],warnings,actual
            scores=Counter(); mapping={r['id']:r for r in rows}
            for ranked in [sparse[:30],dense[:30]]:
                for rank,row in enumerate(ranked): scores[row['id']]+=1/(60+rank+1)
            fused=[dict(mapping[mid],score=score) for mid,score in sorted(scores.items(),key=lambda x:(-x[1],x[0]))]
            if mode=='rerank' and fused:
                if not (self.model_dir/'reranker/config.json').exists():
                    warnings.append('Reranker unavailable; using hybrid retrieval.'); actual='hybrid'
                else:
                    if self.reranker is None:
                        from sentence_transformers import CrossEncoder
                        self.reranker=CrossEncoder(str(self.model_dir/'reranker'),local_files_only=True,trust_remote_code=False,device='cpu')
                    top=fused[:20]; values=self.reranker.predict([(question,r['text']) for r in top],show_progress_bar=False)
                    fused=sorted([dict(r,score=float(v)) for r,v in zip(top,values)],key=lambda r:(-r['score'],r['id']))
            return fused[:limit],warnings,actual
