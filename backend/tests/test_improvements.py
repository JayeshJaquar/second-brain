import asyncio
import json
import sqlite3
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from brain.store import Store
from brain.api import create_app
from brain.assistant import Assistant, clarification
from brain.retrieval import Retriever
from brain.learning import dashboard, fit_recall
from brain.ingestion import article_text

@pytest.fixture
def store(tmp_path):
    s=Store(tmp_path/'data');yield s;s.db.close()

class Stub:
    def __init__(self,*answers):self.answers=list(answers)
    async def json(self,*args,**kwargs):return self.answers.pop(0)

def test_html_prefers_article_and_preserves_raw_input(store):
    raw='<header>Login</header><nav>Menu</nav><main><article><header><h1>Study</h1></header><p>Review every 17 days.</p><aside>Ad</aside><p hidden>Wrong fact.</p></article></main><footer>Terms</footer>'
    c=TestClient(create_app(store),base_url='http://127.0.0.1:8765')
    result=c.post('/api/memories',headers={'Authorization':'Bearer '+store.token},json={'title':'Study','text':raw,'kind':'html'}).json()
    assert result['raw_text']==raw
    assert result['text']=='Study\nReview every 17 days.'
    assert article_text('<article><p>A<br>B</p><script>bad()</script></article>')=='A\nB'

def test_browser_metadata_survives_without_remote_fetch(store):
    m=store.add(title='Article',source='https://example.com/article',text='A complete source sentence.',kind='article',extraction={'method':'browser-dom','figures':[{'caption':'A diagram'}]})
    assert store.memory(m['id'])['extraction']['method']=='browser-dom'
    store.db.close();s=Store(store.root)
    assert s.memory(m['id'])['extraction']['figures'][0]['caption']=='A diagram';s.db.close()
    store.db=sqlite3.connect(':memory:')

def test_broad_questions_clarify_without_model_or_search(store):
    for question in ['Explain photosynthesis','Tell me about recursion','summarize it','what about that?']:
        r=asyncio.run(Assistant(store,Retriever(store),Stub()).answer(question))
        assert r['status']=='clarify' and not r['citations']
    assert clarification('How does a base case stop recursion?')[0] is None

def test_generated_claims_are_filtered_by_support_check(store):
    store.add(title='Z',source='Synthetic',text='Zorvia reviews every 17 days.')
    llm=Stub({'conflict':False,'evidence_ids':['E1']},{'claims':[{'text':'Reviews happen every 17 days.','evidence_ids':['E1']},{'text':'This raises exam scores by 90 percent.','evidence_ids':['E1']}]},{'supported_claim_indices':[0]})
    result=asyncio.run(Assistant(store,Retriever(store),llm).answer('What is the Zorvia cycle?',mode='lexical',explain=True))
    assert len(result['claims'])==1 and '90 percent' not in json.dumps(result)
    assert any('withheld' in w for w in result['warnings'])

def test_unknown_claim_citation_is_never_displayed(store):
    store.add(title='Z',source='Synthetic',text='Zorvia reviews every 17 days.')
    llm=Stub({'conflict':False,'evidence_ids':['E1']},{'claims':[{'text':'Invented','evidence_ids':['E999']}]})
    result=asyncio.run(Assistant(store,Retriever(store),llm).answer('Zorvia cycle?',mode='lexical',explain=True))
    assert not result['claims']

def test_recalled_answer_correction_and_hint_are_retained_then_cascade(store):
    m=store.add(title='Z',source='Synthetic',text='Review every 17 days.')
    rid=store.save_review(m['id'],'When?',m['text'])
    store.record_review(rid,True,1,'Seven days','I missed the leading one.')
    row=dashboard(store)['reviews'][0]
    assert row['history'][0]['response']=='Seven days'
    assert row['history'][0]['correction']=='I missed the leading one.'
    assert not row['history'][0]['correct'] and row['shadow_interval_days'] is None
    store.delete(m['id']);assert not store.rows('SELECT * FROM events')

def test_shadow_schedule_does_not_activate_on_tiny_holdout():
    events=[{'at':i,'correct':i%2,'elapsed':i%5,'prior':i,'previous_accuracy':.5} for i in range(60)]
    _,m=fit_recall(events)
    assert not m['shadow_eligible'] and m['test_events']==12
    assert m['baseline_log_loss']>=0

def test_schema_v1_upgrade_is_additive_and_idempotent(tmp_path):
    s=Store(tmp_path);m=s.add(title='Old',source='test',text='Preserve this.')
    s.db.execute('ALTER TABLE memories DROP COLUMN extraction_json')
    s.db.execute('ALTER TABLE events DROP COLUMN response');s.db.execute('ALTER TABLE events DROP COLUMN correction')
    s.db.execute('PRAGMA user_version=1');s.db.commit();s.db.close()
    for _ in range(2):
        s=Store(tmp_path);assert s.memory(m['id'])['text']=='Preserve this.'
        assert s.memory(m['id'])['extraction']=={}
        assert s.db.execute('PRAGMA user_version').fetchone()[0]==2;s.db.close()

def test_bare_diagram_labels_do_not_answer_visual_attributes(store):
    store.add(title='Diagram',source='Synthetic',text='Begin Process Finish')
    a=Assistant(store,Retriever(store),Stub())
    for q in ['What color is Finish?','Which arrow connects Begin and Process?','What shape contains Begin?']:
        r=asyncio.run(a.answer(q,mode='lexical'))
        assert r['status']=='abstained' and not r['citations']

def test_explicit_color_statement_remains_answerable(store):
    store.add(title='Diagram notes',source='Synthetic',text='The Finish box is green.')
    a=Assistant(store,Retriever(store),Stub({'conflict':False,'evidence_ids':['E1']}))
    r=asyncio.run(a.answer('What color is the Finish box?',mode='lexical'))
    assert r['status']=='supported' and 'green' in r['message']
