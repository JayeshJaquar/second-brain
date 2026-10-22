"""Frozen source-disjoint evaluation. Uses only original fixtures and local models."""
import argparse
import asyncio
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
import time
import types
import uuid
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from brain.store import Store
from brain.retrieval import Retriever
from brain.assistant import Assistant
from brain.llm import LocalLLM
from brain.config import TEXT_MODEL
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'backend/data/milestone-v3'

def dataset():
    raw=(DATA/'benchmark.json').read_bytes();manifest=json.loads((DATA/'manifest.json').read_text())
    if hashlib.sha256(raw).hexdigest()!=manifest['sha256']:raise ValueError('Frozen benchmark hash mismatch.')
    data=json.loads(raw)
    groups={d['id']:d['split'] for d in data['documents']}
    texts={d['id']:d['text'] for d in data['documents']}
    assert len(groups)==len(data['documents']) and len({c['id'] for c in data['cases']})==len(data['cases'])
    for c in data['cases']:
        for e in c['evidence']:
            assert groups[e['document']]==c['split'] and e['quote'] in texts[e['document']]
    return data,manifest

def baseline_class():
    code=subprocess.check_output(['git','show','18e9e59:backend/brain/retrieval.py'],cwd=ROOT)
    module=types.ModuleType('brain.historical_retrieval');module.__package__='brain'
    exec(compile(code,'historical_retrieval.py','exec'),module.__dict__)
    return module.Retriever,hashlib.sha256(code).hexdigest()

def grade(case,result,reverse):
    gold={(e['document'],e['quote']) for e in case['evidence']}
    returned=[(reverse.get(c['memory_id'],'unknown'),c['quote']) for c in result.get('citations',[])]
    expected=case['expected'];status=result.get('status')
    exact=sum(pair in gold for pair in returned)
    passed=(status=='supported' and set(returned)==gold and (expected!='conflict' or result.get('conflict'))) if gold else (status==expected and not returned)
    return dict(passed=bool(passed),returned_citations=len(returned),gold_matched_citations=exact,
                missing_gold=[{'document':d,'quote':q} for d,q in sorted(gold-set(returned))],
                extra_citations=[{'document':d,'quote':q} for d,q in returned if (d,q) not in gold])

def metrics(cases):
    answerable=[c for c in cases if c['expected'] in ('supported','conflict')]
    missing=[c for c in cases if c['expected']=='abstained']
    cites=sum(c.get('grade',{}).get('returned_citations',0) for c in cases)
    supported=sum(c.get('grade',{}).get('gold_matched_citations',0) for c in cases)
    rate=lambda n,d:n/d if d else None
    return dict(cases=len(cases),passed=sum(c.get('grade',{}).get('passed',False) for c in cases),errors=sum('error' in c for c in cases),
        answerable=len(answerable),unanswerable=len(missing),citations=cites,
        coverage=rate(sum(bool(c.get('result',{}).get('citations')) for c in cases),len(cases)),
        gold_excerpt_match_precision=rate(supported,cites),
        false_refusal_rate=rate(sum(c.get('result',{}).get('status') in ('abstained','clarify','rejected') for c in answerable),len(answerable)),
        unsupported_answer_rate=rate(sum(bool(c.get('result',{}).get('citations')) for c in missing),len(missing)),
        p50_seconds=float(np.percentile([c['seconds'] for c in cases],50)) if cases else None,
        p95_seconds=float(np.percentile([c['seconds'] for c in cases],95)) if cases else None)

async def evaluate(args):
    data,manifest=dataset();Baseline,baseline_hash=baseline_class()
    output=Path(args.output)
    if output.exists():raise ValueError('Refusing to overwrite an evaluation. Choose a new report path.')
    report=dict(dataset=manifest,authorship=data['authorship'],protocol=data['protocol'],started_at=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),working_tree_changed=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)),
        code_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['backend/brain/retrieval.py','backend/brain/assistant.py','backend/brain/store.py']},
        baseline_code_sha256=baseline_hash,model=TEXT_MODEL,python=platform.python_version(),splits={},complete=False,
        limitations=['Agent-authored fictional data; no independent human review.','Test sources are disjoint from development sources, but this is not a large real-world benchmark.',
        'Exact gold-excerpt matching penalizes additional unlabelled context; it does not evaluate generated explanations or factual truth.',
        'Diagram questions test text evidence availability, not visual perception.','Historical retrieval runs on the same prebuilt vectors; timings exclude model initialization.',
        'Answer latency includes local model loading; no cloud calls or personal memories.'])
    def save():output.write_text(json.dumps(report,indent=2)+'\n')
    save()
    for split in args.splits:
        with tempfile.TemporaryDirectory() as tmp:
            s=Store(Path(tmp));ids={d['id']:str(uuid.uuid5(uuid.NAMESPACE_URL,'milestone-v3:'+d['id'])) for d in data['documents'] if d['split']==split};reverse={v:k for k,v in ids.items()}
            for d in data['documents']:
                if d['id'] in ids:s.add(id=ids[d['id']],title=d['id'],source=d['source'],text=d['text'])
            r=Retriever(s);started=time.perf_counter();r.index_pending();prep=time.perf_counter()-started
            old=Baseline(s);old.encoder=r.encoder
            cases=[c for c in data['cases'] if c['split']==split]
            results=dict(index_seconds=prep,models=r.manifest(),retrieval={},cases=[]);report['splits'][split]=results
            for name,engine in [('current',r),('historical',old)]:
                results['retrieval'][name]={}
                for mode in ['lexical','dense','hybrid','rerank']:
                    rankings=[]
                    for c in cases:
                        if not c['evidence']:continue
                        started=time.perf_counter();rows,warnings,actual=engine.search(c['question'],mode,limit=8)
                        gold={(e['document'],e['quote']) for e in c['evidence']}
                        ranked=[(reverse[row['memory_id']],row['text']) for row in rows[:5]]
                        ranks=[i+1 for i,pair in enumerate(ranked) if pair in gold]
                        rankings.append(dict(id=c['id'],seconds=time.perf_counter()-started,mode=actual,warnings=warnings,
                            recall5=len(set(ranked)&gold)/len(gold),rr5=1/min(ranks) if ranks else 0,
                            ranked=[{'document':d,'quote':q} for d,q in ranked]))
                    results['retrieval'][name][mode]=dict(recall5=float(np.mean([q['recall5'] for q in rankings])),mrr5=float(np.mean([q['rr5'] for q in rankings])),queries=rankings)
                    print(split,name,mode,results['retrieval'][name][mode]['recall5'],flush=True)
                if name=='current':old.reranker=r.reranker
            if not args.retrieval_only:
                assistant=Assistant(s,r,LocalLLM())
                for c in cases:
                    started=time.perf_counter();row=dict(c)
                    try:
                        result=await assistant.answer(c['question'],mode='rerank')
                        row.update(result=result,grade=grade(c,result,reverse))
                    except Exception as exc:row.update(error=type(exc).__name__+': '+str(exc))
                    row['seconds']=round(time.perf_counter()-started,3);results['cases'].append(row)
                    results['metrics']=metrics(results['cases']);save()
                    print(c['id'],row.get('grade',{}).get('passed',False),flush=True)
            s.db.close();save()
    report['complete']=True;save()
    print(json.dumps({k:v.get('metrics') for k,v in report['splits'].items()},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    parser.add_argument('--splits',nargs='+',choices=['development','test'],default=['development','test'])
    parser.add_argument('--retrieval-only',action='store_true')
    asyncio.run(evaluate(parser.parse_args()))
