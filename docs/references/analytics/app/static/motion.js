/* KPI rolling digits and staggered spring intro (DESIGN_PLAN section 10). Honours prefers-reduced-motion. */
(function(){
var RM=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches,SPRING='cubic-bezier(.3,1.4,.5,1)';
var seen=false;try{seen=!!sessionStorage.getItem('dfh-intro')}catch(e){}
function isD(c){return c>='0'&&c<='9'}
function roll(el,text,quiet){
  var old=el.dataset.txt||'';el.dataset.txt=text;el.setAttribute('aria-label',text);
  if(RM){el.textContent=text;return}
  if(old.length!==text.length||!el.querySelector('.dg')){
    el.textContent='';
    for(var i=0;i<text.length;i++){var s=document.createElement('span');s.setAttribute('aria-hidden','true');
      if(isD(text[i])){s.className='dg';s.dataset.d='0';var st=document.createElement('span');st.className='st';
        for(var k=0;k<10;k++){var n=document.createElement('i');n.textContent=k;st.appendChild(n)}s.appendChild(st)}
      else s.textContent=text[i];
      el.appendChild(s)}
    old='';
  }
  var ds=el.querySelectorAll('.dg'),j=0;
  for(var i=0;i<text.length;i++){
    if(!isD(text[i]))continue;
    var d=+text[i],sp=ds[j++],from=+sp.dataset.d,to='translateY(-'+d*1.2+'em)';
    if(old!==''&&old[i]===text[i])continue;
    sp.dataset.d=d;
    if(quiet){sp.firstChild.style.transform=to;continue}
    sp.firstChild.style.transform=to;
    sp.firstChild.animate([{transform:'translateY(-'+from*1.2+'em)'},{transform:to}],{duration:900,delay:j*45,easing:SPRING});
  }
}
window.dfhRoll=roll;
document.querySelectorAll('[data-roll]').forEach(function(el){roll(el,el.dataset.roll,seen)});
if(!RM&&!seen){
  try{sessionStorage.setItem('dfh-intro','1')}catch(e){}
  document.querySelectorAll('.tile').forEach(function(t,i){
    t.animate([{opacity:0,transform:'translateY(6px)'},{opacity:1,transform:'none'}],{duration:650,delay:Math.min(i*90,900),easing:SPRING,fill:'backwards'})});
}
var usd=function(n){return n.toLocaleString('en-US',{maximumFractionDigits:0})};
function inr(p){var r=(p||0)/100;return r>=1e5?'\u20b9'+(r/1e5).toFixed(2)+' L':'\u20b9'+usd(r)}
var fmt={revenue_today:inr,aov_today:inr,orders_today:function(p){return usd(p)}};
if(document.querySelector('[data-kpi]'))setInterval(function(){
  if(document.hidden)return;
  fetch('/api/exec').then(function(r){return r.json()}).then(function(j){
    document.querySelectorAll('[data-kpi]').forEach(function(el){var k=el.dataset.kpi;if(j[k]&&j[k].value!=null&&fmt[k])roll(el,fmt[k](j[k].value))})}).catch(function(){})
},30000);
})();
