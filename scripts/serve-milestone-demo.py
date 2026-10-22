"""Disposable local UI fixture. Never opens the personal database; Ctrl-C cleans up."""
import io
import os
import sys
import tempfile
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
os.environ['SECOND_BRAIN_PORT']='8767'
import uvicorn
from brain.store import Store
from brain.api import create_app
from brain.llm import LocalLLM

with tempfile.TemporaryDirectory(prefix='second-brain-milestone-') as temp:
    store=Store(Path(temp))
    # Public synthetic demo credential, valid only for this disposable loopback process.
    store.token='synthetic-milestone-demo-only'
    text='The Sable demo reviews every 31 days.\nA practice attempt comes before the answer reveal.'
    img=Image.new('RGB',(1000,340),'white');draw=ImageDraw.Draw(img)
    draw.text((60,70),'The Sable demo reviews every 31 days.',fill='black',font_size=30)
    draw.text((60,170),'A practice attempt comes before the answer reveal.',fill='black',font_size=26)
    out=io.BytesIO();img.save(out,format='PNG')
    store.add(title='Original citation-inspection demo',source='Original synthetic fixture',text=text,image=out.getvalue(),kind='ocr',ocr=[
        dict(text='The Sable demo reviews every 31 days.',x=.06,y=1-110/340,width=.7,height=40/340,confidence=.98),
        dict(text='A practice attempt comes before the answer reveal.',x=.06,y=1-210/340,width=.85,height=40/340,confidence=.96)])
    try:
        uvicorn.run(create_app(store,LocalLLM()),host='127.0.0.1',port=8767,log_level='warning')
    finally:store.db.close()
