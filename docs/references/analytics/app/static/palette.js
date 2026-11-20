/* Command palette (Cmd/Ctrl+K). Systems from the nav, theme actions, released insights from /api/insights. */
(function(){
var pal=document.getElementById('pal');if(!pal)return;
var inp=pal.querySelector('input'),ul=pal.querySelector('ul'),items=[],view=[],sel=0,last=null,loaded=false;
function base(){var a=[];document.querySelectorAll('.rail a[href]').forEach(function(l){a.push({t:l.querySelector('.t').textContent,k:'System',run:function(){location.href=l.getAttribute('href')}})});
  [['light','Light'],['dark','Dark'],['auto','Auto']].forEach(function(m){a.push({t:'Theme: '+m[1],k:'Action',run:function(){var b=document.querySelector('.seg button[data-m="'+m[0]+'"]');if(b)b.click()}})});return a}
function draw(){var q=inp.value.trim().toLowerCase();view=items.filter(function(i){return!q||(i.t+' '+i.k).toLowerCase().indexOf(q)>-1}).slice(0,12);if(sel>=view.length)sel=0;
  ul.innerHTML='';view.forEach(function(i,n){var li=document.createElement('li');li.id='pal-'+n;li.setAttribute('role','option');li.setAttribute('aria-selected',n===sel);
    var a=document.createElement('span');a.textContent=i.t;var b=document.createElement('small');b.textContent=i.k;li.append(a,b);li.onclick=function(){go(n)};ul.appendChild(li)});
  inp.setAttribute('aria-activedescendant',view.length?'pal-'+sel:'');if(!view.length){var e=document.createElement('li');e.className='none';e.textContent='No match';ul.appendChild(e)}}
function go(n){var i=view[n];if(!i)return;close();i.run()}
function open(){last=document.activeElement;pal.hidden=false;items=base();sel=0;inp.value='';draw();inp.focus();
  if(!loaded){loaded=true;fetch('/api/insights').then(function(r){return r.json()}).then(function(j){j.forEach(function(i){items.push({t:'Insight: '+i.title,k:'Insight',run:function(){if(window.dfhPanel)window.dfhPanel(i.id)}})});if(!pal.hidden)draw()}).catch(function(){loaded=false})}}
function close(){pal.hidden=true;if(last)last.focus()}
document.addEventListener('keydown',function(e){
  if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();pal.hidden?open():close();return}
  if(pal.hidden)return;
  if(e.key==='Escape'){close()}else if(e.key==='ArrowDown'){e.preventDefault();sel=Math.min(sel+1,view.length-1);draw()}else if(e.key==='ArrowUp'){e.preventDefault();sel=Math.max(sel-1,0);draw()}else if(e.key==='Enter'){e.preventDefault();go(sel)}});
inp.addEventListener('input',function(){sel=0;draw()});
pal.addEventListener('mousedown',function(e){if(e.target===pal)close()});
var b=document.getElementById('palbtn');if(b)b.onclick=open;
})();
