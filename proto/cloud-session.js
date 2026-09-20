'use strict';
// Server-signed anonymous cookie. No signup and no personal data in this request.
const dailyQuota={enabled:false,used:null,limit:10,date:null};
let quotaRequest=0;
function quotaDay(){return new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());}
function dailyQuotaText(){return dailyQuota.enabled?`오늘 ${dailyQuota.date===quotaDay()&&Number.isInteger(dailyQuota.used)?dailyQuota.used:'—'}/${dailyQuota.limit}회`:'';}
function paintDailyQuota(){document.querySelectorAll('[data-daily-quota]').forEach(el=>{el.textContent=dailyQuotaText();});}
async function refreshDailyQuota(){
  if(!dailyQuota.enabled)return;
  const request=++quotaRequest;
  try{
    const response=await fetch('/api/session',{cache:'no-store'});
    if(!response.ok)throw new Error('usage unavailable');
    const data=await response.json();
    if(request!==quotaRequest)return;
    dailyQuota.limit=data.dailyLimit||10;dailyQuota.used=data.usage?.used??null;dailyQuota.date=data.usage?.date??null;
  }catch{if(request!==quotaRequest)return;dailyQuota.used=null;}
  paintDailyQuota();
}
window.addEventListener('focus',()=>refreshDailyQuota());
document.addEventListener('visibilitychange',()=>{if(!document.hidden)refreshDailyQuota();});
setInterval(()=>{if(!document.hidden&&dailyQuota.enabled&&dailyQuota.date&&dailyQuota.date!==quotaDay())refreshDailyQuota();},60000);
const cloudSessionReady=(async()=>{
  const health=await fetch('/api/health').then(r=>r.json()).catch(()=>null);
  if(health?.provider!=='gemini')return;
  dailyQuota.enabled=true;
  await refreshDailyQuota();
  // Old invitation bookmarks now open the same public conversation.
  if(new URLSearchParams(location.hash.slice(1)).has('invite')){
    history.replaceState(null,'',location.pathname+location.search+'#chat');
  }
})().catch(error=>{window.janeConnectionError=error.message;});
