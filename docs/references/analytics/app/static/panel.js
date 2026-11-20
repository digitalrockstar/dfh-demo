/* Right-side insight panel. window.dfhPanel(id) opens it; any [data-insight] element triggers it. */
(function(){
var p=document.getElementById('ipanel');if(!p)return;
var body=p.querySelector('.body'),x=p.querySelector('.x'),last=null;
function close(){p.classList.remove('open');p.setAttribute('aria-hidden','true');if(last)last.focus()}
function open(id,from){last=from||document.activeElement;
  fetch('/panel/'+encodeURIComponent(id)).then(function(r){if(!r.ok)throw 0;return r.text()}).then(function(h){body.innerHTML=h;p.classList.add('open');p.setAttribute('aria-hidden','false');x.focus()}).catch(function(){body.textContent='Insight not available.';p.classList.add('open');p.setAttribute('aria-hidden','false')})}
window.dfhPanel=open;
x.onclick=close;document.addEventListener('keydown',function(e){if(e.key==='Escape'&&p.classList.contains('open'))close()});
document.addEventListener('click',function(e){var t=e.target.closest('[data-insight]');if(t){e.preventDefault();open(t.dataset.insight,t)}});
})();
