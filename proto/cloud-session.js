'use strict';
// Server-signed anonymous cookie. No signup and no personal data in this request.
const dailyQuota={enabled:false,used:null,limit:10,date:null};
let quotaFlight=null,quotaNextRead=0,quotaBlockedUntil=0,quotaDirty=false;
function quotaDay(){return new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());}
function dailyQuotaText(){return dailyQuota.enabled?`오늘 ${dailyQuota.date===quotaDay()&&Number.isInteger(dailyQuota.used)?dailyQuota.used:'—'}/${dailyQuota.limit}회`:'';}
function paintDailyQuota(){document.querySelectorAll('[data-daily-quota]').forEach(el=>{el.textContent=dailyQuotaText();});}
function refreshDailyQuota({force=false}={}){
  if(!dailyQuota.enabled)return Promise.resolve();
  if(Date.now()<quotaBlockedUntil)return Promise.resolve();
  if(quotaFlight){if(force)quotaDirty=true;return quotaFlight;}
  if(Date.now()<quotaNextRead&&!force)return Promise.resolve();
  quotaFlight=(async()=>{
    do{
      quotaDirty=false;
      try{
        const response=await fetch('/api/session',{cache:'no-store',signal:AbortSignal.timeout(8000)});
        if(!response.ok){
          const retry=Number(response.headers.get('Retry-After'));
          quotaBlockedUntil=Date.now()+Math.max(60000,Number.isFinite(retry)?retry*1000:0);
          throw new Error('usage unavailable');
        }
        const data=await response.json();
        dailyQuota.limit=data.dailyLimit||10;dailyQuota.used=data.usage?.used??null;dailyQuota.date=data.usage?.date??null;
        quotaNextRead=Date.now()+10000;
      }catch{
        dailyQuota.used=null;quotaDirty=false;
        quotaBlockedUntil=Math.max(quotaBlockedUntil,Date.now()+60000);
      }
      paintDailyQuota();
    }while(quotaDirty);
  })().finally(()=>{quotaFlight=null;});
  return quotaFlight;
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
