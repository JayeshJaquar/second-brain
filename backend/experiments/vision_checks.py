"""Controlled diagram check. Generated fixture contains no personal information."""
import asyncio
import io
import json
import sys
import tempfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from brain.store import Store
from brain.vision import describe
from brain.llm import LocalLLM
root=Path(__file__).resolve().parents[2]
async def main():
 image=Image.new('RGB',(1000,400),'white'); draw=ImageDraw.Draw(image)
 font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',28)
 for x,label in [(40,'Study'),(370,'Practice'),(700,'Review')]:
  draw.rounded_rectangle((x,120,x+250,240),radius=15,fill='#dbeafe',outline='#1e3a8a',width=3); draw.text((x+40,160),label,fill='black',font=font)
 for x in [300,630]:
  draw.line((x,180,x+55,180),fill='black',width=5); draw.polygon([(x+55,180),(x+40,168),(x+40,192)],fill='black')
 draw.text((40,40),'Zorvia learning cycle',fill='black',font=font)
 draw.text((40,300),'Review every 17 days',fill='black',font=font)
 buf=io.BytesIO();image.save(buf,format='PNG')
 with tempfile.TemporaryDirectory() as tmp:
  s=Store(Path(tmp));m=s.add(title='Synthetic diagram',source='Original fixture',text='',image=buf.getvalue())
  result=await describe(s,LocalLLM(),m['id']); text=json.dumps(result).lower()
  report={'scope':'One original synthetic diagram; not a multimodal benchmark.','result':result,
      'labels_present':all(w in text for w in ['study','practice','review']),'timing_fact_present':'17' in text,
      'not_promoted_to_text_evidence':not s.candidates(m['id'])}
  s.db.close()
 (root/'test-results/vision-v1.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
 assert report['labels_present'] and report['timing_fact_present'] and report['not_promoted_to_text_evidence'], 'Controlled diagram check failed; inspect vision-v1.json.'
asyncio.run(main())
