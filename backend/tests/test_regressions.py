import asyncio
import io
import json
import uuid
from pathlib import Path
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from brain.store import Store
from brain.api import create_app
from brain.retrieval import Retriever
from brain.assistant import Assistant
from brain.agent import Agent
from brain.vision import describe

@pytest.fixture
def store(tmp_path):
 s=Store(tmp_path/'data');yield s;s.db.close()

class MutatingLLM:
 def __init__(self,store,mid):self.store=store;self.mid=mid
 async def json(self,*a,**kw):
  self.store.delete(self.mid)
  return {'conflict':False,'evidence_ids':['E1']}

def test_delete_during_answer_discards_stale_evidence(store):
 m=store.add(title='Test',source='Synthetic',text='Zorvia needs 17 days.')
 result=asyncio.run(Assistant(store,Retriever(store),MutatingLLM(store,m['id'])).answer('Zorvia',mode='lexical'))
 assert result['status']=='abstained' and not result['citations']

def test_corrupt_migration_does_not_replace_original(store):
 p=store.root/'memories.json';p.write_text('broken')
 with pytest.raises(ValueError):store.migrate_legacy()
 assert p.read_text()=='broken' and not store.list()

def test_image_dedup_reference_count(store):
 buf=io.BytesIO();Image.new('RGB',(10,10),'white').save(buf,format='PNG')
 a=store.add(title='A',source='A',text='',image=buf.getvalue());b=store.add(title='B',source='B',text='',image=buf.getvalue())
 path=store.image_path(a['id']);store.delete(a['id']);assert path.exists();store.delete(b['id']);assert not path.exists()

def test_schema_rejects_unknown_tools_without_execution(store):
 class Bad:
  async def json(self,*a,**kw):return {'tool':'shell','query':'echo bad'}
 with pytest.raises(ValueError):asyncio.run(Agent(store,Retriever(store),Bad()).run('Plan'))
 assert not store.rows('SELECT * FROM traces')

def test_visual_output_is_not_retrieval_evidence(store):
 buf=io.BytesIO();Image.new('RGB',(10,10),'white').save(buf,format='PNG')
 m=store.add(title='Image',source='test',text='',image=buf.getvalue())
 class Vision:
  async def json(self,*a,**kw):
   assert kw['image'];return {'labels':['Study'],'relationships':[],'uncertainty':'Small test image'}
 r=asyncio.run(describe(store,Vision(),m['id']))
 assert not r['used_in_answers'] and not store.candidates()
 assert store.rows('SELECT * FROM vision')
 store.delete(m['id']);assert not store.rows('SELECT * FROM vision')

def test_request_limits_and_bad_retention_do_not_mutate(store):
 c=TestClient(create_app(store),base_url='http://127.0.0.1:8765');auth={'Authorization':'Bearer '+store.token}
 assert c.post('/api/memories',headers={**auth,'Content-Length':'30000001'},content='').status_code==413
 assert c.post('/api/retention/delete',headers=auth,json={'ids':[],'confirm':False}).status_code==422
 assert c.get('/api/retention?days=0',headers=auth).status_code==400
 assert not store.list()
