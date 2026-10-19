// Self-contained because Chrome serializes this function into its isolated world.
export function extractArticle() {
  const visible = node => {
    const style = getComputedStyle(node);
    return node.getClientRects().length > 0 && !node.closest('[hidden],[aria-hidden="true"]') && style.display !== 'none' && style.visibility !== 'hidden';
  };
  const candidates = Array.from(document.querySelectorAll('article,main,[role="main"]')).filter(visible);
  const root = candidates.sort((a,b) => b.innerText.length-a.innerText.length)[0] || document.body;
  const selection = String(window.getSelection() || '').trim();
  const excluded = 'nav,aside,footer,form,button,script,style,noscript,template,[hidden],[aria-hidden="true"]';
  // Collect text from the original DOM to preserve layout and computed visibility.
  const blocks = Array.from(root.querySelectorAll('h1,h2,h3,h4,p,li,pre,figcaption,td'))
    .filter(n => visible(n) && !n.closest(excluded) && !(root === document.body && n.closest('header')))
    .filter(n => !n.parentElement.closest('p,li,pre,td'));
  const text = selection || blocks.map(n => n.innerText.trim()).filter(Boolean).join('\n\n');
  if (!text.trim()) throw new Error('No readable article found. Select the relevant text or use a screenshot.');
  if (text.length > 200000) throw new Error('Article is too large. Select a smaller section.');
  const source = new URL(location.href); source.hash = ''; source.search = '';
  const title = (root.querySelector('h1')?.innerText || document.title || 'Browser article').trim().slice(0,300);
  const published = document.querySelector('meta[property="article:published_time"]')?.content || root.querySelector('time[datetime]')?.getAttribute('datetime') || null;
  return {format:'second-brain-article-v1',title,source:source.href,text,kind:'article',published_at:published?.slice(0,40),
    extraction:{method:selection?'browser-selection':'browser-dom',selector:root.tagName.toLowerCase(),captured_at:new Date().toISOString(),
      characters:text.length,figures:Array.from(root.querySelectorAll('figure')).filter(visible).slice(0,30).map(f=>({caption:f.querySelector('figcaption')?.innerText||'',alt:f.querySelector('img')?.alt||''})),
      warning:'Text from the loaded page only. Image pixels are not included; use native capture for diagrams. Review for private information.'}};
}
