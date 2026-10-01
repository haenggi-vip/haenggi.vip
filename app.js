(() => {
'use strict';
const reduced=matchMedia('(prefers-reduced-motion: reduce)');
const cards=[...document.querySelectorAll('.app-card')];
const button=document.querySelector('#motion-toggle');
const video=document.querySelector('#hero-video');
let videoFrame=0,videoLoaded=false;
let paused=reduced.matches,pending=false,engine;
const clamp=n=>Math.min(1,Math.max(0,n));
// The fixed background remains visible beyond the hero. Its timeline therefore
// follows the entire document, independently of the skill's short pinned intro.
function syncVideo(){
 videoFrame=0;
 if(paused||reduced.matches||video.readyState<2||video.seeking||!Number.isFinite(video.duration))return;
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
 cards.forEach(card=>{const p=paused||reduced.matches?1:clamp((innerHeight-card.getBoundingClientRect().top)/(innerHeight*.26));card.style.opacity=.12+.88*p;card.style.transform=`translateY(${(1-p)*22}px) rotateX(${(1-p)*5}deg)`;});
}
function schedule(){if(!pending){pending=true;requestAnimationFrame(render);}}
function applyMotion(){const off=paused||reduced.matches;document.body.classList.toggle('motion-off',off);button.setAttribute('aria-pressed',String(off));button.textContent=off?'Scroll-Animation aktivieren':'Bewegung reduzieren';engine?.layout();loadVideo();schedule();}
button.addEventListener('click',()=>{paused=!paused;applyMotion();});
reduced.addEventListener('change',()=>{paused=reduced.matches;applyMotion();});
addEventListener('scroll',schedule,{passive:true});addEventListener('resize',schedule,{passive:true});
if(window.CoolWebsite)engine=window.CoolWebsite.mount(document.body);
applyMotion();addEventListener('load',()=>engine?.layout());
})();
