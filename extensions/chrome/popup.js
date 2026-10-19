import {extractArticle} from './extract.js';
const $=id=>document.getElementById(id);
let article;
$('capture').onclick=async()=>{
  $('capture').disabled=true; $('preview').hidden=true;
  try {
    const [tab]=await chrome.tabs.query({active:true,currentWindow:true});
    if (!tab?.id || !/^https?:/.test(tab.url||'')) throw Error('Choose a normal article tab first.');
    const [result]=await chrome.scripting.executeScript({target:{tabId:tab.id},func:extractArticle});
    if (!result?.result) throw Error('Chrome could not read this page. Use native screenshot capture.');
    article=result.result;
    $('title').value=article.title; $('source').value=article.source; $('text').value=article.text;
    $('details').textContent=article.extraction.warning; $('preview').hidden=false;
    $('status').textContent=`Preview ready: ${article.text.length} characters. Nothing saved.`;
  } catch(e) { $('status').textContent=e.message; }
  finally { $('capture').disabled=false; }
};
$('download').onclick=()=>{
  if(!article || !$('text').value.trim()) return;
  const payload={...article,title:$('title').value.slice(0,300),text:$('text').value};
  const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));
  const a=document.createElement('a');a.href=url;a.download='second-brain-article.json';a.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);$('status').textContent='Exported. Review and save it in Learning Studio.';
};
