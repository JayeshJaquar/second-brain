import asyncio
import json
import httpx
from .config import TEXT_MODEL


class LocalLLM:
    def __init__(self): self.lock=asyncio.Lock()
    async def json(self, system, payload, schema, model=TEXT_MODEL, image=None):
        user={'role':'user','content':json.dumps(payload,ensure_ascii=False)}
        if image: user['images']=[image]
        async with self.lock:
            async with httpx.AsyncClient(trust_env=False,follow_redirects=False,timeout=180) as client:
                response=await client.post('http://127.0.0.1:11434/api/chat',json={
                    'model':model,'stream':False,'keep_alive':0,'format':schema,
                    'options':{'temperature':0,'seed':42,'num_ctx':8192,'num_predict':1400},
                    'messages':[{'role':'system','content':system},user]})
                response.raise_for_status()
                return json.loads(response.json()['message']['content'])
