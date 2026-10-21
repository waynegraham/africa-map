/** Prefer generated research routes on loopback previews; keep public URLs portable. */
const loopback=hostname=>['localhost','127.0.0.1','[::1]'].includes(hostname);
export function localMapHref(href,pageUrl,available){
 const page=new URL(pageUrl);
 if(!available||!loopback(page.hostname))return href;
 let target;try{target=new URL(href,page);}catch{return href;}
 if(target.origin!==page.origin||!target.pathname.endsWith('/research_map/index.html'))return href;
 return '/outputs/research_map_maplibre/index.html'+target.search+target.hash;
}

async function useLocalResearchLinks(){
 if(!loopback(location.hostname))return;
 try{
  const response=await fetch('/outputs/research_map_maplibre/build_manifest.json',{cache:'no-store'});
  if(!response.ok)return;
  const manifest=await response.json();
  if(!manifest.purpose?.startsWith('Local MapLibre'))return;
  const rewrite=()=>{for(const a of document.querySelectorAll('a[href]')){const href=a.getAttribute('href'),next=localMapHref(href,location.href,true);if(next!==href)a.setAttribute('href',next);}};
  rewrite();
  // National profiles create their pilot links after their record is selected.
  new MutationObserver(rewrite).observe(document.body,{childList:true,subtree:true});
 }catch{/* A docs-only preview keeps its public snapshot links. */}
}
if(typeof document!=='undefined')useLocalResearchLinks();
