import asyncio
import base64
import hmac
import json
import time
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field, ConfigDict
from .config import DATA, PORT
from .store import Store
from .retrieval import Retriever
from .assistant import Assistant
from .agent import Agent
from .llm import LocalLLM
from .learning import dashboard
from .topics import TopicClassifier
from .ingestion import article_text
from .vision import describe

class MemoryInput(BaseModel):
    title: str=Field(min_length=1,max_length=300)
    source: str=Field(default='Manual note',max_length=2000)
    text: str=Field(default='',max_length=200000)
    screenshotPNG: str | None=Field(default=None,max_length=28000000)
    kind: Literal['note','ocr','article','html']='note'
    published_at: str | None=Field(default=None,max_length=40)
    extraction: dict=Field(default_factory=dict)
    ocr: list[dict]=Field(default_factory=list,max_length=5000)

class Question(BaseModel):
    question: str=Field(min_length=1,max_length=800)
    memory_id: str | None=None
    mode: Literal['lexical','dense','hybrid','rerank']='rerank'
    explain: bool=False

class ReviewInput(BaseModel):
    memory_id: str
    prompt: str=Field(min_length=1,max_length=500)
    answer: str=Field(min_length=1,max_length=2000)
class ReviewResult(BaseModel):
    correct: bool
    hints: int=Field(default=0,ge=0,le=20)
    response: str=Field(default='',max_length=4000)
    correction: str=Field(default='',max_length=4000)
class Goal(BaseModel):
    goal: str=Field(min_length=1,max_length=800)
class Topic(BaseModel):
    topic: str=Field(min_length=1,max_length=80)
class Retention(BaseModel):
    ids: list[str]=Field(max_length=500)
    confirm: Literal[True]


def create_app(store=None,llm=None):
    store=store or Store(DATA); store.migrate_legacy()
    retriever=Retriever(store); llm=llm or LocalLLM(); assistant=Assistant(store,retriever,llm); agent=Agent(store,retriever,llm)
    app=FastAPI(title='Second Brain local engine',docs_url=None,redoc_url=None,openapi_url=None)
    app.state.store=store; app.state.retriever=retriever
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost'])
    gate=asyncio.Semaphore(1)
    @app.middleware('http')
    async def boundaries(request: Request, call_next):
        if request.headers.get('origin') not in {None,f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}'}:
            return JSONResponse({'detail':'Cross-origin requests are not accepted.'},status_code=403)
        if request.url.path.startswith('/api/') and not hmac.compare_digest(request.headers.get('authorization',''),'Bearer '+store.token):
            return JSONResponse({'detail':'Local authorization required.'},status_code=401)
        try: size=int(request.headers.get('content-length','0'))
        except ValueError: return JSONResponse({'detail':'Invalid request length.'},status_code=400)
        if size>30_000_000:
            return JSONResponse({'detail':'Request too large.'},status_code=413)
        response=await call_next(request)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
        return response
    def auth(authorization: str | None=Header(default=None)):
        if not authorization or not hmac.compare_digest(authorization,'Bearer '+store.token):
            raise HTTPException(401,'Open Learning Studio from Second Brain, or enter your local token.')
    @app.exception_handler(KeyError)
    async def missing(request,exc): return JSONResponse({'detail':'Memory or review no longer exists.'},status_code=404)
    @app.exception_handler(ValueError)
    async def invalid(request,exc): return JSONResponse({'detail':str(exc)},status_code=400)
    @app.get('/health')
    def health(): return {'service':'second-brain','version':'0.3.0'}
    @app.get('/')
    def ui(): return FileResponse(Path(__file__).parent/'web/index.html')
    @app.get('/studio.js')
    def js(): return FileResponse(Path(__file__).parent/'web/studio.js',media_type='text/javascript')
    @app.get('/studio.css')
    def css(): return FileResponse(Path(__file__).parent/'web/studio.css',media_type='text/css')
    @app.get('/api/memories',dependencies=[Depends(auth)])
    def memories(): return store.list()
    @app.post('/api/memories',dependencies=[Depends(auth)])
    def save(data: MemoryInput):
        text=article_text(data.text) if data.kind=='html' else data.text
        memory=store.add(title=data.title,source=data.source,text=text,kind=data.kind,published_at=data.published_at,
            image=base64.b64decode(data.screenshotPNG,validate=True) if data.screenshotPNG else None,ocr=data.ocr,
            raw_text=data.text,extraction=data.extraction)
        topic=TopicClassifier().predict(memory['text'])
        with store.lock,store.db: store.db.execute("UPDATE memories SET topic=? WHERE id=? AND topic='unclassified'",(topic,memory['id']))
        return store.memory(memory['id'])
    @app.get('/api/memories/{mid}',dependencies=[Depends(auth)])
    def memory(mid: str): return store.memory(mid)
    @app.get('/api/memories/{mid}/image',dependencies=[Depends(auth)])
    def image(mid: str): return FileResponse(store.image_path(mid),media_type='image/png')
    @app.delete('/api/memories/{mid}',dependencies=[Depends(auth)])
    def delete(mid: str): store.delete(mid); return {'deleted':True,'legacy_backup_retained':True}
    @app.patch('/api/memories/{mid}/topic',dependencies=[Depends(auth)])
    def topic(mid: str,data: Topic):
        store.memory(mid)
        with store.lock,store.db: store.db.execute('UPDATE memories SET topic=? WHERE id=?',(data.topic,mid))
        return store.memory(mid)
    @app.post('/api/ask',dependencies=[Depends(auth)])
    async def ask(data: Question):
        try:
            async with gate: return await assistant.answer(data.question,data.memory_id,data.mode,data.explain)
        except (ValueError,KeyError): raise
        except Exception: raise HTTPException(503,'Local model unavailable or returned invalid output. No generated answer was accepted. Check Ollama and the installed model.')
    @app.get('/api/learning',dependencies=[Depends(auth)])
    def learning(): return dashboard(store)
    @app.post('/api/reviews',dependencies=[Depends(auth)])
    def review(data: ReviewInput): return {'id':store.save_review(data.memory_id,data.prompt,data.answer)}
    @app.post('/api/reviews/{rid}/result',dependencies=[Depends(auth)])
    def result(rid: str,data: ReviewResult): return store.record_review(rid,data.correct,data.hints,data.response,data.correction)
    @app.post('/api/agent',dependencies=[Depends(auth)])
    async def plan(data: Goal):
        try:
            async with gate: return await agent.run(data.goal)
        except Exception: raise HTTPException(503,'Local agent stopped: invalid output or unavailable model. No quiz was saved.')
    @app.post('/api/memories/{mid}/vision',dependencies=[Depends(auth)])
    async def vision(mid: str):
        store.image_path(mid)
        try:
            async with gate: return await describe(store,llm,mid)
        except Exception: raise HTTPException(503,'Local vision model unavailable or invalid result. Install qwen2.5vl:3b; no image was sent to a cloud service.')
    @app.get('/api/retention',dependencies=[Depends(auth)])
    def retention(days: int=90):
        if not 1<=days<=3650: raise HTTPException(400,'Use 1–3650 days.')
        return {'candidates':store.rows('SELECT id,title,created_at FROM memories WHERE created_at<?',(time.time()-days*86400,)),
            'warning':'Preview only. Deletion also removes chunks, embeddings, reviews and visual descriptions. Legacy JSON and external backups remain.'}
    @app.post('/api/retention/delete',dependencies=[Depends(auth)])
    def purge(data: Retention):
        for mid in data.ids: store.memory(mid)
        for mid in data.ids: store.delete(mid)
        return {'deleted':len(data.ids)}
    @app.get('/api/status',dependencies=[Depends(auth)])
    def status():
        return {'database':'SQLite + FTS5','schema':2,'memories':len(store.list()),'chunks':store.rows('SELECT count(*) AS n FROM chunks')[0]['n'],
            'models':retriever.manifest(),'legacy_backup':(store.root/'memories.json').exists(),
            'privacy':'Local only. No automatic URL fetching. Original JSON backup is retained. Capture permissions belong to the native app.'}
    return app
