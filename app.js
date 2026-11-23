(() => {
'use strict';
const english=document.documentElement.lang==='en';
const cards=[...document.querySelectorAll('.app-card')];
const buttons=[...document.querySelectorAll('[data-motion-toggle],#motion-toggle')];
const video=document.querySelector('#hero-video');
let videoFrame=0,videoLoaded=false;
// Every visit starts with the requested cinematic scroll effect enabled.
// Pausing applies only to the currently open page.
let paused=false,pending=false;
let targetProgress=0,smoothProgress=0,scrubFrame=0;
const cardState=new WeakMap();
const clamp=n=>Math.min(1,Math.max(0,n));
// The fixed background remains visible beyond the hero. Its timeline therefore
// follows the entire document, with smooth LERP scrubbing over All-Intra frames.
function syncVideo(){
 videoFrame=0;
 if(document.hidden||paused||video.readyState<1||!Number.isFinite(video.duration))return;
 const diff=targetProgress-smoothProgress;
 smoothProgress=Math.abs(diff)<0.0008?targetProgress:smoothProgress+diff*0.22;
 const target=smoothProgress*Math.max(0,video.duration-0.04);
 if(!video.seeking&&Math.abs(video.currentTime-target)>.008)video.currentTime=target;
 if(Math.abs(targetProgress-smoothProgress)>=0.0008)queueVideo();
}
function queueVideo(){if(!videoFrame)videoFrame=requestAnimationFrame(syncVideo);}
function loadVideo(){
 if(videoLoaded||paused)return;
 videoLoaded=true;
 const source=innerWidth<=600?video.dataset.scrollSrcMobile:video.dataset.scrollSrc;
 video.preload='auto';
 // Fetch once as a blob so arbitrary scroll seeks never stall on range requests.
 // Fall back to the native URL only if fetch fails or times out.
 const controller=new AbortController();
 const timeout=setTimeout(()=>controller.abort(),45000);
 fetch(source,{signal:controller.signal}).then(response=>{
  if(!response.ok)throw new Error('Video unavailable');
  return response.blob();
 }).then(blob=>{
  video.src=URL.createObjectURL(blob);
  video.load();
 }).catch(()=>{
  video.src=source;
  video.load();
 }).finally(()=>clearTimeout(timeout));
}
video.addEventListener('loadeddata',()=>{document.body.classList.add('video-ready');queueVideo();});
['loadedmetadata','canplay','progress','seeked'].forEach(event=>video.addEventListener(event,queueVideo));
video.addEventListener('error',()=>document.body.classList.remove('video-ready'));
addEventListener('pageshow',queueVideo);
function render(){
 pending=false;
 document.body.classList.toggle('header-scrolled',scrollY>32);
 const progress=clamp(scrollY/Math.max(1,document.documentElement.scrollHeight-innerHeight));
 targetProgress=progress;
 queueVideo();
 document.querySelector('#scroll-value').textContent=String(Math.round(progress*100)).padStart(2,'0');
 document.querySelector('#progress-fill').style.transform=`scaleY(${progress})`;
 // Batch all layout reads first, then write transforms only when changed.
 const vh=innerHeight;
 const next=cards.map(card=>paused?1:clamp((vh-card.getBoundingClientRect().top)/(vh*.24)));
 cards.forEach((card,i)=>{
  const p=Math.round(next[i]*100)/100;
  if(cardState.get(card)===p)return;
  cardState.set(card,p);
  card.style.transform=p>=1?'none':`translate3d(0,${((1-p)*14).toFixed(1)}px,0)`;
 });
}
function schedule(){if(!pending){pending=true;requestAnimationFrame(render);}}
function applyMotion(){
 document.body.classList.toggle('motion-off',paused);
 buttons.forEach(button=>{
  button.setAttribute('aria-pressed',String(paused));
  const label=english?(paused?'Enable scroll video':'Pause scroll video'):(paused?'Scroll-Video aktivieren':'Scroll-Video pausieren');
  button.innerHTML='<span class="motion-label"></span>';
  button.firstChild.textContent=label;
  button.title=label;
 });
 loadVideo();schedule();
}
if(matchMedia('(hover: hover)').matches){
 cards.forEach(card=>{
  card.addEventListener('pointermove',event=>{
   if(paused)return;
   const rect=card.getBoundingClientRect();
   card.style.setProperty('--mx',`${event.clientX-rect.left}px`);
   card.style.setProperty('--my',`${event.clientY-rect.top}px`);
  },{passive:true});
 });
}
buttons.forEach(button=>button.addEventListener('click',()=>{
 paused=!paused;
 applyMotion();
}));
addEventListener('scroll',schedule,{passive:true});addEventListener('resize',schedule,{passive:true});
const published=cards.filter(card=>card.dataset.platforms);
const filters=[...document.querySelectorAll('[data-filter]')];
function filterApps(value){
 published.forEach(card=>card.hidden=value!=='all'&&!card.dataset.platforms.split(' ').includes(value));
 filters.forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.filter===value)));
 document.querySelector('#result-count').textContent=`${published.filter(card=>!card.hidden).length} ${english?'apps':'Apps'}`;
 ['engineering','digital'].forEach(id=>{const section=document.getElementById(id);section.hidden=![...section.querySelectorAll('[data-platforms]')].some(card=>!card.hidden);});
 schedule();
}
filters.forEach(button=>button.addEventListener('click',()=>filterApps(button.dataset.filter)));
document.querySelector('.filter-bar').hidden=false;
document.querySelectorAll('.app-dock a').forEach(link=>link.addEventListener('click',()=>filterApps('all')));
// Animate internal navigation explicitly so browser/OS smooth-scroll settings
// cannot turn an Apps click into an immediate anchor jump. Video follows scrollY.
let navigationFrame=0;
function cancelNavigation(){cancelAnimationFrame(navigationFrame);navigationFrame=0;}
['wheel','touchstart','pointerdown'].forEach(event=>addEventListener(event,cancelNavigation,{passive:true}));
addEventListener('keydown',event=>{if(['Escape','ArrowUp','ArrowDown','PageUp','PageDown','Home','End',' '].includes(event.key))cancelNavigation();});
document.querySelectorAll('a[href^="#"]').forEach(link=>link.addEventListener('click',event=>{
 if(event.defaultPrevented||event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;
 const target=document.getElementById(link.hash.slice(1));
 if(!target)return;
 event.preventDefault();cancelNavigation();
 if(target.hidden||target.closest('[hidden]'))filterApps('all');
 const start=scrollY;
 const offset=parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop)||0;
 const destination=Math.max(0,Math.min(document.documentElement.scrollHeight-innerHeight,start+target.getBoundingClientRect().top-offset));
 const distance=destination-start;
 const duration=Math.min(1600,Math.max(850,Math.abs(distance)*.65));
 const began=performance.now();
 history.pushState(null,'',link.hash);
 // Language links retain the same section after switching languages.
 dispatchEvent(new HashChangeEvent('hashchange'));
 function step(now){
  const progress=clamp((now-began)/duration);
  const eased=progress<.5?4*progress**3:1-(-2*progress+2)**3/2;
  window.scrollTo({top:start+distance*eased,behavior:'instant'});
  schedule();
  if(progress<1)navigationFrame=requestAnimationFrame(step);
  else{
   navigationFrame=0;
   if(!target.hasAttribute('tabindex'))target.setAttribute('tabindex','-1');
   target.focus({preventScroll:true});
  }
 }
 navigationFrame=requestAnimationFrame(step);
}));
addEventListener('hashchange',()=>{if(published.some(card=>'#'+card.id===location.hash&&card.hidden))filterApps('all');});
document.addEventListener('visibilitychange',()=>{if(!document.hidden)schedule();});
applyMotion();
})();
