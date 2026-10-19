'use strict';
const $=id=>document.getElementById(id);
let importedExtraction={};
let token=sessionStorage.getItem('brain-token')||'';
const hash=new URLSearchParams(location.hash.slice(1));
if(hash.has('token')){token=hash.get('token');sessionStorage.setItem('brain-token',token);history.replaceState(null,'',location.pathname);}
$('token').value=token;
function el(tag,text){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;}
function button(text,action){const n=el('button',text);n.onclick=()=>run(n,action);return n;}
async function api(path,data,method){const r=await fetch('/api/'+path,{method:method||(data?'POST':'GET'),headers:{'Authorization':'Bearer '+token,'Content-Type':'application/json'},body:data?JSON.stringify(data):undefined});if(!r.ok){let e=await r.json();throw Error(typeof e.detail==='string'?e.detail:JSON.stringify(e.detail));}return r.json();}
async function run(btn,action){btn.disabled=true;$('status').textContent='Working locally…';try{await action();$('status').textContent='Ready.';}catch(e){$('status').textContent=e.message;}finally{btn.disabled=false;}}
function tab(name){for(const id of ['ask','library','practice','planner','privacy'])$(id).hidden=id!==name;document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('active',b.dataset.tab===name));}
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{tab(b.dataset.tab);if(b.dataset.tab==='library')run(b,library);if(b.dataset.tab==='practice')run(b,practice);});tab('ask');
$('connect').onclick=()=>run($('connect'),async()=>{token=$('token').value.trim();await api('status');sessionStorage.setItem('brain-token',token);$('login').hidden=true;});
if(token){$('login').hidden=true;api('status').catch(e=>{$('login').hidden=false;$('status').textContent=e.message;});}
$('askButton').onclick=()=>run($('askButton'),async()=>{const r=await api('ask',{question:$('question').value,mode:$('mode').value,explain:$('explain').checked});$('answer').replaceChildren(el('p',r.status==='supported'?(r.conflict?'Sources may disagree — compare the excerpts.':'Evidence found'):r.message));for(const suggestion of r.suggestions||[])$('answer').append(button(suggestion,async()=>{$('question').value=suggestion;}));for(const c of r.citations){const a=el('article');a.append(el('blockquote',c.quote),el('small',`[${c.id}] ${c.title} · ${c.source}`),button('Open source',()=>detail(c.memory_id)));$('answer').append(a);}for(const c of r.claims||[])$('answer').append(el('p','Generated interpretation: '+c.text+' ['+c.evidence_ids.join(', ')+']'));$('answer').append(el('small',`Search: ${r.mode}; ${r.candidate_count} passages. `+r.warnings.join(' ')));});
async function library(){const rows=await api('memories');$('memories').replaceChildren();for(const m of rows){const a=el('article');a.append(el('strong',m.title),el('p',`${m.topic} · ${new Date(m.created_at*1000).toLocaleDateString()}${m.screened?' · excluded from AI: instruction patterns':''}`),button('Open',()=>detail(m.id)));$('memories').append(a);}}
$('refreshLibrary').onclick=()=>run($('refreshLibrary'),library);
$('saveMemory').onclick=()=>run($('saveMemory'),async()=>{await api('memories',{title:$('title').value,source:$('source').value||'Manual note',text:$('content').value,kind:$('kind').value,published_at:$('published').value||null,extraction:importedExtraction});$('content').value='';importedExtraction={};await library();});
async function detail(id){const m=await api('memories/'+id);tab('library');const panel=$('memoryDetail');panel.replaceChildren(el('h2',m.title),el('small',m.source+' · Captured '+new Date(m.created_at*1000).toLocaleString()+(m.published_at?' · Published '+m.published_at:'')),el('p',m.text));
 if(m.has_image){const response=await fetch(`/api/memories/${id}/image`,{headers:{Authorization:'Bearer '+token}});if(!response.ok)throw Error('Cannot load image');const img=el('img');img.alt='Stored source screenshot';const url=URL.createObjectURL(await response.blob());img.onload=()=>URL.revokeObjectURL(url);img.src=url;panel.append(img,button('Interpret diagram locally (experimental)',async()=>{const r=await api(`memories/${id}/vision`,{});panel.append(el('pre',JSON.stringify(r,null,2)));}));}
 const details=el('details');details.append(el('summary','Original extraction and confidence'),el('pre',JSON.stringify({raw_text:m.raw_text,ocr:m.ocr,extraction:m.extraction},null,2)));panel.append(details);
 const topic=el('input');topic.value=m.topic;topic.setAttribute('aria-label','Correct topic');panel.append(topic,button('Correct topic',async()=>{await api(`memories/${id}/topic`,{topic:topic.value},'PATCH');await library();}));
 const question=el('input');question.placeholder='Write a practice question';question.setAttribute('aria-label','Practice question');const answer=el('textarea');answer.placeholder='Paste the exact answer excerpt from this memory';answer.setAttribute('aria-label','Source answer');panel.append(question,answer,button('Save practice question',async()=>{await api('reviews',{memory_id:id,prompt:question.value,answer:answer.value});question.value='';answer.value='';}));
 panel.append(button('Delete memory',async()=>{if(confirm('Delete this memory, image and dependent practice data? Original backups remain.')){await api('memories/'+id,null,'DELETE');panel.replaceChildren();$('answer').replaceChildren();$('drafts').replaceChildren();$('trace').textContent='';$('reviews').replaceChildren();await library();}}));panel.scrollIntoView({behavior:'smooth'});}
async function practice(){
 const r=await api('learning');
 $('learningStatus').textContent=r.model.message+' '+r.schedule;
 $('learningMetrics').textContent=JSON.stringify(r.model,null,2);
 $('reviews').replaceChildren();
 for(const q of r.reviews){
  const a=el('article');a.append(el('h3',q.prompt),el('small',`${q.title} · ${q.due_now?'Due now':'Next: '+new Date(q.due*1000).toLocaleDateString()} · ${q.attempts} attempts`));
  const response=el('textarea');response.placeholder='Try answering before revealing (optional)';response.setAttribute('aria-label','Your recalled answer');
  const p=el('p',q.answer);p.hidden=true;const rate=el('div');rate.hidden=true;
  const hint=el('label');const check=el('input');check.type='checkbox';hint.append(check,document.createTextNode(' I used a hint'));rate.append(hint);
  const correction=el('textarea');correction.placeholder='What did you miss or correct? (optional)';correction.setAttribute('aria-label','Correction after reveal');rate.append(correction);
  for(const correct of [true,false])rate.append(button(correct?'I recalled it':'I need practice',async()=>{
   await api(`reviews/${q.id}/result`,{correct,hints:check.checked?1:0,response:response.value,correction:correction.value});await practice();
  }));
  a.append(response,button('Reveal answer',async()=>{response.disabled=true;p.hidden=false;rate.hidden=false;}),p,rate);
  if(q.recall_probability!==null)a.append(el('p',`Experimental recall estimate: ${Math.round(q.recall_probability*100)}%`));
  if(q.shadow_interval_days!==null)a.append(el('p',`Comparison only: learned suggestion ${q.shadow_interval_days} days; current rule interval ${q.interval} days. Your schedule has not changed.`));
  if(q.history?.length){const history=el('details');history.append(el('summary','Recent answers and corrections'));for(const h of q.history)history.append(el('p',`${new Date(h.at*1000).toLocaleString()} · ${h.correct?'Independent recall':'Needs practice'} · Hints: ${h.hints}\nYour answer: ${h.response||'(not entered)'}\nCorrection: ${h.correction||'(none)'}`));a.append(history);}
  $('reviews').append(a);
 }
}
$('refreshPractice').onclick=()=>run($('refreshPractice'),practice);
$('planButton').onclick=()=>run($('planButton'),async()=>{const r=await api('agent',{goal:$('goal').value});$('trace').textContent=JSON.stringify(r.steps,null,2);$('drafts').replaceChildren(el('p',`Stopped: ${r.stopped}. Nothing saved automatically.`));for(const d of r.drafts){const a=el('article');a.append(el('h3',d.prompt),el('p',d.answer),button('Save this practice question',async()=>{await api('reviews',d);a.append(el('small','Saved.'));}));$('drafts').append(a);}});
$('refreshStatus').onclick=()=>run($('refreshStatus'),async()=>{$('storage').textContent=JSON.stringify(await api('status'),null,2);});
$('previewRetention').onclick=()=>run($('previewRetention'),async()=>{const r=await api('retention?days='+encodeURIComponent($('days').value));$('retention').replaceChildren(el('p',r.warning));for(const m of r.candidates)$('retention').append(el('p',m.title));if(r.candidates.length)$('retention').append(button(`Delete these ${r.candidates.length} memories`,async()=>{if(confirm('Permanently delete the listed memories from the active store?')){await api('retention/delete',{ids:r.candidates.map(m=>m.id),confirm:true});$('retention').replaceChildren(el('p','Deleted from active store.'));$('answer').replaceChildren();$('drafts').replaceChildren();$('trace').textContent='';$('reviews').replaceChildren();$('memoryDetail').replaceChildren();$('memories').replaceChildren();}}));});

function previewArticle(data){
 if(data.format!=='second-brain-article-v1'||typeof data.text!=='string'||!data.text.trim()||data.text.length>200000||typeof data.title!=='string'||!data.title.trim()||typeof data.source!=='string')throw Error('This is not a supported Second Brain article export.');
 const source=new URL(data.source);if(!['http:','https:'].includes(source.protocol))throw Error('The article source must be an HTTP or HTTPS URL.');
 $('title').value=data.title.slice(0,300);$('source').value=source.href.slice(0,2000);$('content').value=data.text;$('kind').value='article';
 $('published').value=typeof data.published_at==='string'?data.published_at.slice(0,10):'';
 importedExtraction={method:'browser-import',exported_metadata:data.extraction||{},review_required:true};
 $('importPreview').open=true;$('importPreview').scrollIntoView({behavior:'smooth'});
}
$('articleFile').onchange=()=>run($('saveMemory'),async()=>{
 const file=$('articleFile').files[0];if(!file)return;
 if(file.size>1500000)throw Error('Choose an article export smaller than 1.5 MB.');
 previewArticle(JSON.parse(await file.text()));$('articleFile').value='';
});
$('previewJson').onclick=()=>run($('previewJson'),async()=>{
 if($('articleJson').value.length>1500000)throw Error('Choose an export smaller than 1.5 MB.');
 previewArticle(JSON.parse($('articleJson').value));$('articleJson').value='';
});
