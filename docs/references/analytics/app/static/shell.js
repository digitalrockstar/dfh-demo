(function(){
var root=document.documentElement,seg=document.querySelectorAll('.seg button');
function apply(m){try{localStorage.setItem('dfh-theme',m)}catch(e){}root.dataset.mode=m;root.dataset.theme=m==='auto'?(matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light'):m;seg.forEach(function(b){b.setAttribute('aria-pressed',b.dataset.m===m)})}
seg.forEach(function(b){b.onclick=function(){apply(b.dataset.m)}});apply(root.dataset.mode||'auto');
var ev=document.getElementById('evtime'),feed=document.getElementById('feed');
if(!window.EventSource)return;
var es=new EventSource('/stream');
es.onopen=function(){ev.textContent='Stream connected'};es.onerror=function(){ev.textContent='Stream reconnecting'};
es.onmessage=function(m){var e=JSON.parse(m.data),t=new Date(e.ts*1000).toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'Asia/Kolkata'});
ev.textContent='Last event '+t+' IST';
if(!feed)return;var li=document.createElement('li'),a=document.createElement('time'),b=document.createElement('span');a.textContent=t;b.textContent=e.message+(e.prov==='live'||e.prov==='derived'?' ('+e.prov+')':'');li.append(a,b);feed.prepend(li);while(feed.children.length>40)feed.lastChild.remove()};
})();
