(function(){
var R=document.documentElement,RM=matchMedia('(prefers-reduced-motion:reduce)').matches;
function $(s,e){return Array.prototype.slice.call((e||document).querySelectorAll(s))}
/* smooth monotone-cubic spline (no overshoot) */
function mono(p){var n=p.length,m=[],e=[],i,o;for(i=0;i<n-1;i++)e[i]=(p[i+1][1]-p[i][1])/(p[i+1][0]-p[i][0]);m[0]=e[0];m[n-1]=e[n-2];for(i=1;i<n-1;i++)m[i]=e[i-1]*e[i]<=0?0:(e[i-1]+e[i])/2;for(i=0;i<n-1;i++){if(e[i]===0){m[i]=m[i+1]=0}else{var a=m[i]/e[i],b=m[i+1]/e[i],s=a*a+b*b;if(s>9){var t=3/Math.sqrt(s);m[i]=t*a*e[i];m[i+1]=t*b*e[i]}}}
o='M'+p[0][0].toFixed(1)+' '+p[0][1].toFixed(1);for(i=0;i<n-1;i++){var dx=(p[i+1][0]-p[i][0])/3;o+='C'+(p[i][0]+dx).toFixed(1)+' '+(p[i][1]+m[i]*dx).toFixed(1)+' '+(p[i+1][0]-dx).toFixed(1)+' '+(p[i+1][1]-m[i+1]*dx).toFixed(1)+' '+p[i+1][0].toFixed(1)+' '+p[i+1][1].toFixed(1)}return o}
$('.spark polyline').forEach(function(l){var p=l.getAttribute('points').trim().split(/\s+/).map(function(x){return x.split(',').map(Number)}),e=document.createElementNS('http://www.w3.org/2000/svg','path');e.setAttribute('d',mono(p));e.setAttribute('fill','none');e.setAttribute('stroke',l.getAttribute('stroke'));e.setAttribute('stroke-width','1.2');e.setAttribute('vector-effect','non-scaling-stroke');l.parentNode.replaceChild(e,l)});
/* v3: system shell (rail icons, groups, system strip) */
var IC={'Executive MIS':'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z','Sales & Channels':'M3 17l6-6 4 4 8-8M15 7h6v6','Products & Inventory':'M21 8l-9-5-9 5v8l9 5 9-5zM3 8l9 5 9-5M12 13v8','Customers':'M16 19v-1a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v1M10 10a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7M20 19v-1a3 3 0 0 0-2-2.8','Marketing':'M3 10v4l11 5V5zM14 9c3 .5 5 1.5 5 3s-2 2.5-5 3','Finance':'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18M14.5 9.5c-.5-1-1.5-1.5-2.5-1.5-1.4 0-2.5.8-2.5 2s1 1.8 2.5 2 2.5.8 2.5 2-1.1 2-2.5 2c-1 0-2-.5-2.5-1.5','Procurement & Supply Chain':'M2 6h11v10H2zM13 9h4l3 3v4h-7M6 19a1.5 1.5 0 1 0 0-.01M17 19a1.5 1.5 0 1 0 0-.01','Operations':'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1','People':'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8M4 21c0-4 3.5-6 8-6s8 2 8 6','Technology & IT':'M7 7h10v10H7zM9 3v4M15 3v4M9 17v4M15 17v4M3 9h4M3 15h4M17 9h4M17 15h4','Data Management':'M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3M4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6','Growth & Planning':'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8M12 12h.01','Reports & Settings':'M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M14 4v4M8 10v4M16 16v4'};
var rl=$('.rail')[0];if(rl){var GP={'Executive MIS':'Command','Sales & Channels':'Commerce','Finance':'Business','Technology & IT':'Platform'};
$('a',rl).forEach(function(a){var n=a.getAttribute('aria-label'),ic=$('.ic',a)[0];ic.innerHTML='<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="'+IC[n]+'"/></svg>';if(GP[n]){var h=document.createElement('div');h.className='grp';h.textContent=GP[n];rl.insertBefore(h,a)}});
var rf=document.createElement('div');rf.className='rfoot';rf.innerHTML='<i class="dot"></i>Simulated event stream';rl.appendChild(rf)}
var pl=$('.pulse')[0];if(pl){var sgm=$('.seg',pl)[0];pl.innerHTML='<span><i class="dot"></i><b>Engine</b> running</span><span>Events <b data-sys="ev">1,240</b>/min</span><span>p95 latency <b data-sys="lat">184</b> ms</span><span>Jobs <b>3</b> running</span><span>Freshness <b>98%</b></span><span data-live="window"></span><span class="badge sim">Simulated</span><span class="sp"></span><span data-sys="clock"></span>';pl.appendChild(sgm)}
/* theme */
var th='auto';try{th=localStorage.getItem('dfh-theme')||'auto'}catch(e){}
function ap(m){m==='auto'?R.removeAttribute('data-theme'):R.setAttribute('data-theme',m);$('.seg button').forEach(function(b){b.classList.toggle('on',b.dataset.m===m)})}
ap(th);$('.seg button').forEach(function(b){b.onclick=function(){try{localStorage.setItem('dfh-theme',b.dataset.m)}catch(e){}ap(b.dataset.m)}});
/* motion: spring from rest (zeta .55, ~12% overshoot) */
function sp(p){if(p<=0)return 0;if(p>=1)return 1;var z=.55,w=11,wd=w*Math.sqrt(1-z*z);function x(t){return 1-Math.exp(-z*w*t)*(Math.cos(wd*t)+z*w/wd*Math.sin(wd*t))}return x(p)/x(1)}
/* pseudo-real-time model: every timestamp is relative to now (D-30..D+14) */
var DAY=864e5,B=new Date();B.setHours(0,0,0,0);
function dt(d){var x=new Date(B);x.setDate(x.getDate()+d);return x}
function rng(s){return function(){s|=0;s=s+0x6D2B79F5|0;var t=Math.imul(s^s>>>15,1|s);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
function nz(d,k){return rng(Math.floor(dt(d).getTime()/DAY)*7+k)()-.5}
var WK=[1.2,.88,.86,.9,.95,1.05,1.22];
function rev(d){return 6.2*(1+.004*(d+30))*WK[dt(d).getDay()]*(1+(d<=0?nz(d,1)*.14:0))}
function web(d){return rev(d)*(.13+.02*Math.sin(d/5))}
function ads(d){return d<=0?.9*1.12*WK[dt(d).getDay()]*(1+nz(d,3)*.1):.9*WK[dt(d).getDay()]}
var S=[],s=700;for(var d=-30;d<=14;d++){if(d===-20||d===-8||d===7)s+=600;s=Math.max(0,s-55*(1+(d<=0?nz(d,2)*.1:0)));S.push(s)}
function frac(){var n=new Date(),h=n.getHours()+n.getMinutes()/60+n.getSeconds()/3600,f=Math.min(1,Math.max(0,(h-9)/12));return .04+.96*(3*f*f-2*f*f*f)}
function arr(f){var a=[];for(var d=-30;d<=14;d++)a.push(f(d));return a}
var CH={rev:{u:function(v){return'₹'+v.toFixed(2)+' L'},s:[{v:arr(rev),c:'var(--accent)',f:1},{v:arr(web),c:'var(--signal)'}]},
ord:{u:function(v){return Math.round(v).toLocaleString('en-IN')+' orders'},s:[{v:arr(function(d){return rev(d)*1e5/600}),c:'var(--info)',f:1}]},
stk:{u:function(v){return Math.round(v)+' kg'},s:[{v:S,c:'var(--signal)',f:1}],mk:[{i:37,t:'PO-1182 due, 3 days late',c:'var(--warn)'}],z:1},
ads:{u:function(v){return'₹'+v.toFixed(2)+' L'},s:[{v:arr(ads),c:'var(--accent)'},{v:arr(function(d){return .9*WK[dt(d).getDay()]}),c:'var(--t2)',dash:1}]}};
function fd(i){return dt(i-30).toLocaleDateString('en-IN',{weekday:'short',day:'numeric',month:'short'})}
var CID=0;function chart(el){var cid="c"+(++CID),c=CH[el.dataset.k],W=+el.dataset.w||600,H=190,n=45,all=[].concat.apply([],c.s.map(function(q){return q.v})),mx=Math.max.apply(0,all)*1.1,mn=c.z||el.dataset.k!=='ads'?0:Math.min.apply(0,all)*.8;
function X(i){return i*W/(n-1)}function Y(v){return H-18-(v-mn)/(mx-mn)*(H-30)}
function P(v,a,b){var p=[];for(var i=a;i<=b;i++)p.push([X(i),Y(v[i])]);return mono(p)}
var g='<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="Daily trend, 30 days back to 14 days ahead"><defs>'+c.s.map(function(q,i){return'<linearGradient id="'+cid+i+'" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="'+q.c+'" stop-opacity=".32"/><stop offset="1" stop-color="'+q.c+'" stop-opacity="0"/></linearGradient>'}).join('')+'<filter id="'+cid+'s" x="-5%" y="-20%" width="110%" height="160%"><feDropShadow dy="4" stdDeviation="3" flood-opacity=".3"/></filter></defs><g stroke="var(--border)"><path d="M0 40H'+W+'M0 90H'+W+'M0 140H'+W+'"/></g><rect x="'+X(30)+'" y="0" width="'+(W-X(30))+'" height="'+(H-18)+'" fill="var(--border)" opacity=".35"/>';
if(c.z)S.forEach(function(v,i){if(i>30&&v===0)g+='<rect x="'+(X(i)-W/88)+'" y="0" width="'+(W/44)+'" height="'+(H-18)+'" fill="var(--neg)" opacity=".18"/>'});
c.s.forEach(function(q,qi){if(q.f)g+='<path d="'+P(q.v,0,30)+'L'+X(30)+' '+(H-18)+'L0 '+(H-18)+'Z" fill="url(#'+cid+qi+')"/>';
if(q.dash)g+='<path d="'+P(q.v,0,44)+'" fill="none" stroke="'+q.c+'" stroke-width="1" stroke-dasharray="4 4"/>';else g+='<path d="'+P(q.v,0,30)+'" fill="none" stroke="'+q.c+'" stroke-width="1.4" filter="url(#'+cid+'s)"/><path d="'+P(q.v,30,44)+'" fill="none" stroke="'+q.c+'" stroke-width="1.1" stroke-dasharray="4 4"/>'});
(c.mk||[]).forEach(function(m){g+='<path d="M'+X(m.i)+' 6V'+(H-18)+'" stroke="'+m.c+'" stroke-dasharray="2 3"/><text x="'+(X(m.i)-6)+'" y="12" text-anchor="end">'+m.t+'</text>'});
g+='<path d="M'+X(30)+' 0V'+(H-18)+'" stroke="var(--signal)" stroke-width="1"/><circle cx="'+X(30)+'" cy="'+Y(c.s[0].v[30])+'" r="5" fill="var(--signal)">'+(RM?'':'<animate attributeName="r" values="4;7;4" dur="2s" repeatCount="indefinite"/>')+'</circle><text x="'+(X(30)+6)+'" y="'+(H-4)+'">Now</text><text x="0" y="'+(H-4)+'">'+fd(0).slice(5)+'</text><text x="'+W+'" y="'+(H-4)+'" text-anchor="end">'+fd(44).slice(5)+'</text><path id="hl" d="" stroke="var(--t2)"/><text class="rd" id="rd" x="4" y="12"></text></svg>';
el.innerHTML=g;var sv=el.firstChild,hl=sv.querySelector('#hl'),rd=sv.querySelector('#rd');
sv.onmousemove=function(e){var r=sv.getBoundingClientRect(),i=Math.max(0,Math.min(44,Math.round((e.clientX-r.left)/r.width*(n-1))));hl.setAttribute('d','M'+X(i)+' 0V'+(H-18));rd.textContent=fd(i)+(i>30?' · forecast ':' · ')+c.u(c.s[0].v[i]);rd.setAttribute('x',X(i)>300?X(i)-6:X(i)+6);rd.setAttribute('text-anchor',X(i)>300?'end':'start')};
sv.onmouseleave=function(){hl.setAttribute('d','');rd.textContent=''}}
$('.chart').forEach(chart);
/* rolling digits */
function roll(el,v){var o=el._s;el._s=v;el.setAttribute('aria-label',v);var ch=v.split(''),ok=o&&o.length===v.length&&ch.every(function(c,i){return/\d/.test(c)===/\d/.test(o[i])});
if(!ok){el.innerHTML=ch.map(function(c){return/\d/.test(c)?'<span class="rc" aria-hidden="true"><span class="col">'+[0,1,2,3,4,5,6,7,8,9].map(function(x){return'<b>'+x+'</b>'}).join('')+'</span></span>':'<span class="ch" aria-hidden="true">'+(c===' '?'&nbsp;':c)+'</span>'}).join('');o=v.replace(/\d/g,'0')}
var cols=$('.col',el),k=0;ch.forEach(function(c,i){if(!/\d/.test(c))return;var col=cols[k++],a=+o[i],b=+c;col.style.transform='translateY(-'+b*1.2+'em)';if(a!==b&&!RM){var f=[];for(var j=0;j<=24;j++)f.push({transform:'translateY('+(-(a+(b-a)*sp(j/24))*1.2)+'em)'});col.animate(f,{duration:700,delay:k*30,easing:'linear',fill:'backwards'})}})}
/* live values */
function tick(){var f=frac(),r=rev(0)*f,w={rev:'₹'+r.toFixed(2)+' L',ord:Math.round(r*1e5/600).toLocaleString('en-IN'),cover:((S[29]-55*f)/55).toFixed(1)+' days'};
$('[data-live]').forEach(function(e){var k=e.dataset.live;if(w[k])roll(e,w[k]);
if(k==='revd'){var x=(rev(0)/rev(-7)-1)*100;e.textContent=(x>=0?'▲ ':'▼ ')+Math.abs(x).toFixed(1)+'% vs same day last week';e.className='d '+(x>=0?'up':'dn')}
if(k==='coverTxt')e.textContent=((S[29]-55*f)/55).toFixed(1)+' days of cover left';
if(k==='window')e.textContent='Window D-30 to D+14 · today '+dt(0).toLocaleDateString('en-IN',{day:'numeric',month:'short'});
if(k==='refresh')e.textContent='Last refresh '+Math.floor((Date.now()/1000)%30)+' s ago'})}
/* intro: staggered spring, first load only */
if(!RM)$('.tile').forEach(function(t,i){var k=[];for(var j=0;j<=30;j++){var s=sp(j/30);k.push({transform:'translateY('+(6*(1-s)).toFixed(2)+'px) scale('+(.86+.14*s).toFixed(4)+')',opacity:Math.min(1,1-Math.pow(2,-10*j/30))})}t.animate(k,{duration:900,delay:i*45,easing:'linear',fill:'backwards'})});
tick();setInterval(tick,1000);
/* signal stream: item times relative to now */
var f=document.getElementById('feed');
function add(txt,ago,sim){var l=document.createElement('li'),d=new Date(Date.now()-ago*1000);l.innerHTML='<time>'+d.toTimeString().slice(0,5)+'</time><span>'+(sim?'<span class="badge sim">Simulated</span> ':'')+txt+'</span>';f.appendChild(l);return l}
if(f){[[60,'Sales mart refreshed in 38 s'],[700,'Anomaly: Mumbai franchise returns 2.4x usual'],[1900,'Insight formed: Almond stock-out risk'],[3600,'PO-1182 delivery moved by 3 days'],[5400,'Daily brief ready for the MD']].forEach(function(x){add(x[1],x[0])});
var m=['Website order batch processed (42 orders)','Franchise stock sync completed: Pune Camp','Basket size up 6% in Koramangala store','Price check: cashew W320 vs last 7 days'],i=0;
if(!RM)setInterval(function(){var l=add(m[i++%m.length],0,1);f.insertBefore(l,f.firstChild)},6000)}
/* v3: 3D donuts and rings, tilt, live throughput */
var UID=0;
function donut(el){var pr=el.dataset.parts.split('|').map(function(p){var a=p.split(':');return{n:a[0],v:+a[1],c:a[2],t:a[3]}}),gg=el.hasAttribute('data-gauge'),tot=pr.reduce(function(s,p){return s+p.v},0),R=70,C=2*Math.PI*R,gap=gg?0:2.5,dep=gg?9:14,id='dn'+(++UID),off=0,arcs=[];
function pc(i){return Math.round(pr[i].v/tot*1000)/10+'%'}
pr.forEach(function(p){var l=p.v/tot*C,d=Math.max(0,l-gap);arcs.push('<circle r="'+R+'" fill="none" stroke="'+p.c+'" stroke-width="26" stroke-dasharray="'+d.toFixed(2)+' '+(C-d).toFixed(2)+'" stroke-dashoffset="'+(-off).toFixed(2)+'" transform="rotate(-90)"/>');off+=l});
var sides='';for(var k=dep;k>=1;k-=1.5)sides+='<g transform="translate(0 '+(k/.56).toFixed(2)+')">'+arcs.join('')+'</g>';
var top=arcs.map(function(a,i){return'<g class="sg" data-i="'+i+'">'+a+'</g>'}).join('');
el.innerHTML='<svg viewBox="0 20 220 140" role="img" aria-label="'+(el.dataset.label||pr.map(function(p,i){return p.n+' '+pc(i)}).join(', '))+'"><defs><linearGradient id="'+id+'" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".34"/><stop offset=".5" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".18"/></linearGradient><filter id="'+id+'b" x="-30%" y="-100%" width="160%" height="300%"><feGaussianBlur stdDeviation="7"/></filter><filter id="'+id+'d"><feColorMatrix type="matrix" values=".55 0 0 0 0 0 .55 0 0 0 0 0 .55 0 0 0 0 0 1 0"/></filter></defs><ellipse cx="110" cy="'+(130+dep)+'" rx="86" ry="11" fill="#000" opacity=".38" filter="url(#'+id+'b)"/><g transform="translate(110 76) scale(1 .56)"><g filter="url(#'+id+'d)">'+sides+'</g>'+top+'<circle r="'+R+'" fill="none" stroke="url(#'+id+')" stroke-width="26" style="pointer-events:none"/><circle r="'+(R+13)+'" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="1" style="pointer-events:none"/></g></svg><div class="ctr"></div>';
var ct=el.querySelector('.ctr');function def(){ct.innerHTML=el.dataset.center?'<b>'+el.dataset.center+'</b>'+(el.dataset.sub?'<span>'+el.dataset.sub+'</span>':''):''}def();
function hot(i){$('.sg',el).forEach(function(s,j){s.classList.toggle('hot',j===i)});if(i<0)def();else ct.innerHTML='<b>'+(pr[i].t||pc(i))+'</b><span>'+pr[i].n+' · '+pc(i)+'</span>'}
if(!gg){$('.sg',el).forEach(function(s,i){s.onmouseenter=function(){hot(i)};s.onmouseleave=function(){hot(-1)}});
if(el.hasAttribute('data-legend')){var ul=document.createElement('ul');ul.className='lg';ul.innerHTML=pr.map(function(p){return'<li><i style="background:'+p.c+'"></i><span>'+p.n+'</span><b>'+(p.t||'')+' '+(p.t?'· ':'')+(Math.round(p.v/tot*1000)/10)+'%</b></li>'}).join('');el.parentNode.appendChild(ul);$('li',ul).forEach(function(l,i){l.onmouseenter=function(){hot(i)};l.onmouseleave=function(){hot(-1)}})}}
if(!RM)el.firstChild.animate([{opacity:0,transform:'translateY(10px) scale(.94)'},{opacity:1,transform:'none'}],{duration:700,delay:200,easing:'cubic-bezier(.3,1.4,.5,1)',fill:'backwards'})}
$('.donut').forEach(donut);
/* pointer tilt with specular glare */
if(!RM)$('.kpi,.d3t').forEach(function(t){t.addEventListener('pointermove',function(e){var r=t.getBoundingClientRect(),x=(e.clientX-r.left)/r.width,y=(e.clientY-r.top)/r.height;t.style.setProperty('--ry',((x-.5)*7).toFixed(2)+'deg');t.style.setProperty('--rx',((.5-y)*7).toFixed(2)+'deg');t.style.setProperty('--mx',(x*100)+'%');t.style.setProperty('--my',(y*100)+'%')});t.addEventListener('pointerleave',function(){t.style.setProperty('--rx','0deg');t.style.setProperty('--ry','0deg')})});
/* live throughput (simulated): scrolls one point per second */
var TP=[],tpE=$('[data-tp]');function evf(t){return 1240+90*Math.sin(t/11)+60*(rng(Math.floor(t))()-.5)}
for(var q=0;q<60;q++)TP.push(evf(Date.now()/1000-60+q));
function drawTp(){tpE.forEach(function(e){var W=300,H=110,mn=1050,mx=1450,P=mono(TP.map(function(v,i){return[i*W/59,H-8-(v-mn)/(mx-mn)*(H-16)]}));e.innerHTML='<svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="none" role="img" aria-label="Events per minute, last 60 seconds"><defs><linearGradient id="tpg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--signal)" stop-opacity=".3"/><stop offset="1" stop-color="var(--signal)" stop-opacity="0"/></linearGradient><filter id="tps" x="-5%" y="-20%" width="110%" height="160%"><feDropShadow dy="3" stdDeviation="2.5" flood-opacity=".3"/></filter></defs><path d="'+P+'L'+W+' '+H+'L0 '+H+'Z" fill="url(#tpg)"/><path d="'+P+'" fill="none" stroke="var(--signal)" stroke-width="1.2" vector-effect="non-scaling-stroke" filter="url(#tps)"/></svg>'})}
function sys(){var t=Date.now()/1000,v=evf(t);TP.shift();TP.push(v);drawTp();$('[data-sys=ev]').forEach(function(e){e.textContent=Math.round(v).toLocaleString('en-IN')});$('[data-sys=lat]').forEach(function(e){e.textContent=170+Math.round(30*rng(Math.floor(t)+5)())});$('[data-sys=clock]').forEach(function(e){e.textContent=new Date().toLocaleTimeString('en-IN',{hour12:false})+' IST'})}
sys();setInterval(sys,1000);
})();
