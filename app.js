(() => {
'use strict';
const english=document.documentElement.lang==='en';
const reduced=matchMedia('(prefers-reduced-motion: reduce)');
const cards=[...document.querySelectorAll('.app-card')];
const button=document.querySelector('#motion-toggle');
const video=document.querySelector('#hero-video');
let videoFrame=0,videoLoaded=false;
let savedMotion=false;
try{savedMotion=localStorage.getItem("haenggi-reduced-motion")==="true";}catch{}
let paused=savedMotion,pending=false,engine;
const clamp=n=>Math.min(1,Math.max(0,n));
// The fixed background remains visible beyond the hero. Its timeline therefore
// follows the entire document, without holding the reader in a pinned intro.
function syncVideo(){
 videoFrame=0;
 if(document.hidden||paused||reduced.matches||video.readyState<2||video.seeking||!Number.isFinite(video.duration))return;
 const progress=clamp(scrollY/Math.max(1,document.documentElement.scrollHeight-innerHeight));
 const target=progress*Math.max(0,video.duration-0.05);
 if(Math.abs(video.currentTime-target)>.035)video.currentTime=target;
}
function queueVideo(){if(!videoFrame)videoFrame=requestAnimationFrame(syncVideo);}
function loadVideo(){
 if(videoLoaded||paused||reduced.matches)return;
 videoLoaded=true;
 video.src=innerWidth<=600?video.dataset.scrollSrcMobile:video.dataset.scrollSrc;
 video.load();
}
video.addEventListener('loadeddata',()=>{document.body.classList.add('video-ready');queueVideo();});
video.addEventListener('seeked',queueVideo);
video.addEventListener('error',()=>document.body.classList.remove('video-ready'));
addEventListener('pageshow',queueVideo);
function render(){
 pending=false;
 queueVideo();
 const progress=clamp(scrollY/Math.max(1,document.documentElement.scrollHeight-innerHeight));
 document.querySelector('#scroll-value').textContent=Math.round(progress*100);
 document.querySelector('#progress-fill').style.transform=`scaleY(${progress})`;
 cards.forEach(card=>{const p=paused||reduced.matches?1:clamp((innerHeight-card.getBoundingClientRect().top)/(innerHeight*.26));card.style.opacity=.65+.35*p;card.style.transform=`perspective(1000px) translateY(${(1-p)*18}px) rotateX(${(1-p)*3}deg)`;});
}
function schedule(){if(!pending){pending=true;requestAnimationFrame(render);}}
function applyMotion(){const off=paused||reduced.matches;document.body.classList.toggle('motion-off',off);button.setAttribute('aria-pressed',String(off));button.disabled=reduced.matches;button.textContent=english?(reduced.matches?'Motion reduced (system)':off?'Enable scroll animation':'Reduce motion'):(reduced.matches?'Bewegung reduziert (System)':off?'Scroll-Animation aktivieren':'Bewegung reduzieren');engine?.layout();loadVideo();schedule();}
button.addEventListener('click',()=>{paused=!paused;try{localStorage.setItem('haenggi-reduced-motion',String(paused));}catch{}applyMotion();});
reduced.addEventListener('change',()=>{applyMotion();});
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
addEventListener('hashchange',()=>{if(published.some(card=>'#'+card.id===location.hash&&card.hidden))filterApps('all');});
document.addEventListener('visibilitychange',()=>{if(!document.hidden)schedule();});
if(window.CoolWebsite)engine=window.CoolWebsite.mount(document.body);
applyMotion();addEventListener('load',()=>engine?.layout());
})();
