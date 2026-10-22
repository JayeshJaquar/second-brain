"""Source support, false refusals and unsupported answers, with explicit denominators."""
import asyncio
import hashlib
import json
import sys
import tempfile
import time
import uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from brain.store import Store
from brain.retrieval import Retriever
from brain.assistant import Assistant
from brain.llm import LocalLLM
root=Path(__file__).resolve().parents[2]
async def main():
    path=root/'backend/data/answer-cases-v2.json';data=json.loads(path.read_text())
    report={'scope':data['scope'],'dataset_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'model':'qwen2.5:7b-instruct','cases':[]}
    with tempfile.TemporaryDirectory() as temp:
        s=Store(Path(temp));ids={d['id']:str(uuid.uuid5(uuid.NAMESPACE_URL,'second-brain-answers-v2:'+d['id'])) for d in data['documents']}
        reverse={v:k for k,v in ids.items()}
        for d in data['documents']:s.add(id=ids[d['id']],title=d['id'],source='Original synthetic fixture',text=d['text'],published_at=d.get('published_at'))
        retriever=Retriever(s); retriever.index_pending()
        a=Assistant(s,retriever,LocalLLM())
        for case in data['cases']:
            started=time.perf_counter()
            try:
                result=await a.answer(case['question'],ids.get(case.get('scope')))
                sources={reverse[c['memory_id']] for c in result['citations']}
                expected=case['expected']
                if expected in {'supported','conflict'}:
                    passed=result['status']=='supported' and set(case['sources'])==sources and case.get('contains','').lower() in result['message'].lower()
                    if expected=='conflict':passed=passed and result['conflict']
                else:passed=result['status']==expected and not result['citations']
                row={'id':case['id'],'expected':expected,'passed':bool(passed),'seconds':round(time.perf_counter()-started,2),'result':result}
            except Exception as e:row={'id':case['id'],'expected':case['expected'],'passed':False,'error':type(e).__name__+': '+str(e)}
            report['cases'].append(row);print(case['id'],row['passed'],flush=True)
        s.db.close()
    answerable=[c for c in report['cases'] if c['expected'] in {'supported','conflict'}]
    missing=[c for c in report['cases'] if c['expected']=='abstained']
    returned=[c for c in report['cases'] if c.get('result',{}).get('citations')]
    report['metrics']={'total':len(report['cases']),'passed':sum(c['passed'] for c in report['cases']),
        'answerable_count':len(answerable),'unanswerable_count':len(missing),'returned_answers':len(returned),
        'supported_answer_rate':sum(c['passed'] for c in answerable)/len(answerable),
        'false_refusal_rate':sum(not c.get('result',{}).get('citations') for c in answerable)/len(answerable),
        'false_support_rate':sum(bool(c.get('result',{}).get('citations')) for c in missing)/len(missing),
        'source_selection_precision':sum(c['passed'] for c in returned)/len(returned) if returned else None}
    (root/'test-results/answer-quality-v2.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['metrics'],indent=2))
    if not all(c['passed'] for c in report['cases']):sys.exit(1)
asyncio.run(main())
