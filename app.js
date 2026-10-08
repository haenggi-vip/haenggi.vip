(() => {
'use strict';
const english=document.documentElement.lang==='en';
const cards=[...document.querySelectorAll('.app-card')];
const buttons=[...document.querySelectorAll('[data-motion-toggle],#motion-toggle')];
const video=document.querySelector('#hero-video');
let videoFrame=0,videoLoaded=false;
// Every visit starts with the requested cinematic scroll effect enabled.
// Pausing applies only to the currently open page.
let paused=false,pending=false,engine;
const clamp=n=>Math.min(1,Math.max(0,n));
// The fixed background remains visible beyond the hero. Its timeline therefore
// follows the entire document, without holding the reader in a pinned intro.
function syncVideo(){
 videoFrame=0;
 if(document.hidden||paused||video.readyState<1||video.seeking||!Number.isFinite(video.duration))return;
 const progress=clamp(scrollY/Math.max(1,document.documentElement.scrollHeight-innerHeight));
 const target=progress*Math.max(0,video.duration-0.05);
 if(Math.abs(video.currentTime-target)>.035)video.currentTime=target;
}
function queueVideo(){if(!videoFrame)videoFrame=requestAnimationFrame(syncVideo);}
function loadVideo(){
 if(videoLoaded||paused)return;
 videoLoaded=true;
 const source=innerWidth<=600?video.dataset.scrollSrcMobile:video.dataset.scrollSrc;
 video.preload='auto';
 video.src=source;
 video.load();
 // A fully downloaded source supports arbitrary seeks even when a browser or
 // intermediary defers range requests for a paused video. Native URL is fallback.
 const controller=new AbortController();
 const timeout=setTimeout(()=>controller.abort(),45000);
 fetch(source,{signal:controller.signal}).then(response=>{
  if(!response.ok)throw new Error('Video unavailable');
  return response.blob();
 }).then(blob=>{
  video.src=URL.createObjectURL(blob);
  video.load();
 }).catch(()=>{/* Keep the native URL and poster if download fails. */})
 .finally(()=>clearTimeout(timeout));
}
video.addEventListener('loadeddata',()=>{document.body.classList.add('video-ready');queueVideo();});
['loadedmetadata','canplay','progress','seeked'].forEach(event=>video.addEventListener(event,queueVideo));
video.addEventListener('error',()=>document.body.classList.remove('video-ready'));
addEventListener('pageshow',queueVideo);
function render(){
 pending=false;
 queueVideo();
 const progress=clamp(scrollY/Math.max(1,document.documentElement.scrollHeight-innerHeight));
 document.querySelector('#scroll-value').textContent=Math.round(progress*100);
 document.querySelector('#progress-fill').style.transform=`scaleY(${progress})`;
 cards.forEach(card=>{const p=paused?1:clamp((innerHeight-card.getBoundingClientRect().top)/(innerHeight*.26));card.style.opacity=.65+.35*p;card.style.transform=`perspective(1000px) translateY(${(1-p)*18}px) rotateX(${(1-p)*3}deg)`;});
}
function schedule(){if(!pending){pending=true;requestAnimationFrame(render);}}
function applyMotion(){
 document.body.classList.toggle('motion-off',paused);
 buttons.forEach(button=>{
  button.setAttribute('aria-pressed',String(paused));
  button.textContent=english?(paused?'Enable scroll video':'Pause scroll video'):(paused?'Scroll-Video aktivieren':'Scroll-Video pausieren');
 });
 engine?.layout();loadVideo();schedule();
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
if(window.CoolWebsite)engine=window.CoolWebsite.mount(document.body);
applyMotion();addEventListener('load',()=>engine?.layout());
})();
