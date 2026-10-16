"""Storage/keyword scaling smoke check with generated, non-personal documents."""
import json
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from brain.store import Store
from brain.retrieval import Retriever
root=Path(__file__).resolve().parents[2]; result=[]
with tempfile.TemporaryDirectory() as tmp:
 s=Store(Path(tmp)); r=Retriever(s); last=0
 for size in [100,1000,5000]:
  start=time.perf_counter()
  for i in range(last,size): s.add(title=f'Synthetic note {i}',source=f'fixture-{i}',text=f'Lesson {i} describes recursion and a base case. Unique reference identifier number{i}.')
  ingestion=time.perf_counter()-start; start=time.perf_counter(); rows,_,_=r.search(f'number{size-1}','lexical'); query=time.perf_counter()-start
  result.append({'documents':size,'incremental_insert_seconds':ingestion,'keyword_query_seconds':query,'correct_first':bool(rows and f'number{size-1}' in rows[0]['text']),'database_bytes':(s.root/'brain.sqlite3').stat().st_size})
  last=size
 s.db.close()
(root/'test-results/storage-scale-v1.json').write_text(json.dumps({'scope':'Generated small-document smoke test; excludes image volume, dense indexing and concurrent workloads.','measurements':result},indent=2)+'\n')
print(result)
