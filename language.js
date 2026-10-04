(() => {
'use strict';
const current=document.documentElement.lang;
const links=[...document.querySelectorAll('.language-switch a')];
let saved;
const explicit=new URLSearchParams(location.search).get('lang');
try{saved=localStorage.getItem('haenggi-language');}catch{}
// Explicit English URLs remain shareable, regardless of the browser language.
// Only the default entry chooses a language automatically.
if(current==='de'&&explicit!=='de'&&!['de','en'].includes(saved)){
 const preferred=(navigator.languages?.[0]||navigator.language||'de').toLowerCase().startsWith('de')?'de':'en';
 if(preferred==='en'){
  const target=new URL(links.find(link=>link.lang==='en').href);
  target.search=location.search;target.hash=location.hash;
  location.replace(target.href);return;
 }
}else if(current==='de'&&explicit!=='de'&&saved==='en'){
 const target=new URL(links.find(link=>link.lang==='en').href);
 target.search=location.search;target.hash=location.hash;
 location.replace(target.href);return;
}
links.forEach(link=>{
 const target=new URL(link.href);target.searchParams.set('lang',link.lang);target.hash=location.hash;link.href=target.href;
 link.addEventListener('click',()=>{try{localStorage.setItem('haenggi-language',link.lang);}catch{}});
});
addEventListener('hashchange',()=>links.forEach(link=>{const target=new URL(link.href);target.searchParams.set('lang',link.lang);target.hash=location.hash;link.href=target.href;}));
})();
