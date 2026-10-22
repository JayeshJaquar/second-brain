"""Compare indexed/cached retrieval to the original implementation on disposable data."""
import argparse
import hashlib
import json
import platform
import resource
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
import numpy as np
from milestone_benchmark import baseline_class
from brain.store import Store
from brain.retrieval import Retriever
ROOT=Path(__file__).resolve().parents[2]

def main(args):
    path=Path(args.output)
    if path.exists():raise ValueError('Choose a new report path; existing reports are immutable.')
    Baseline,baseline_hash=baseline_class()
    report=dict(description='Original synthetic retrieval-load fixtures; no images or LLM generation.',baseline='18e9e59',baseline_code_sha256=baseline_hash,
        platform=platform.platform(),python=platform.python_version(),repeats=args.repeats,results=[],
        limitations=['One local run, no concurrent LLM workload.','First query means cold retrieval cache with an already-loaded encoder; it is not application startup.',
        'Current and historical engines share encoder weights and stored embeddings.','Dense scoring remains exact and linear in corpus size; this is not an ANN scalability claim.',
        'FTS5 and historical BM25 differ in tokenization/statistics, so ranking equivalence is not assumed.'])
    for size in args.sizes:
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(Path(tmp));began=time.perf_counter()
            for i in range(size):
                store.add(id=str(uuid.uuid5(uuid.NAMESPACE_URL,f'perf-v3:{i}')),title=f'Record {i}',source='Original load fixture',
                    text=f'Project item{i} uses channel group{i%31} for review every {i%89+1} days. Its archive label is code{i%173}.')
            save_seconds=time.perf_counter()-began
            current=Retriever(store);began=time.perf_counter();current.index_pending();index_seconds=time.perf_counter()-began
            old=Baseline(store);old.encoder=current.encoder
            row=dict(memories=size,chunks=len(store.candidates()),save_seconds=save_seconds,index_seconds=index_seconds,models=current.manifest(),modes={})
            for mode in ['lexical','dense','hybrid']:
                row['modes'][mode]={}
                # Alternate engine order by size and mode to reduce consistent order advantage.
                engines=[('historical',old),('current',current)]
                if (args.sizes.index(size)+['lexical','dense','hybrid'].index(mode))%2:engines.reverse()
                for name,r in engines:
                    if name=='current':r.cache=None
                    first=time.perf_counter();r.search('What review interval does project item0 use?',mode);first=time.perf_counter()-first
                    times=[]
                    for j in range(args.repeats):
                        question=f'What review interval does project item{(j*47)%size} use?'
                        start=time.perf_counter();r.search(question,mode);times.append(time.perf_counter()-start)
                    row['modes'][mode][name]=dict(first_seconds=first,p50_seconds=float(np.percentile(times,50)),p95_seconds=float(np.percentile(times,95)),samples_seconds=times)
                print(size,mode,{n:round(v['p95_seconds'],4) for n,v in row['modes'][mode].items()},flush=True)
            row['database_bytes']=(store.root/'brain.sqlite3').stat().st_size
            row['process_peak_rss_mb']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024**2 if sys.platform=='darwin' else 1024)
            report['results'].append(row);path.write_text(json.dumps(report,indent=2)+'\n');store.db.close()
    print('Saved',path,flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--sizes',nargs='+',type=int,default=[1000,5000]);p.add_argument('--repeats',type=int,default=20)
    main(p.parse_args())
