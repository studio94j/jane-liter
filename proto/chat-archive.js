/* Each turn has its own storage key, so another tab cannot overwrite a whole history. */
const ChatArchive=(()=>{
  const prefix='jane-chat-v1:';
  function epoch(author){const key=prefix+author+':epoch';let value=localStorage.getItem(key);if(!value){value=crypto.randomUUID();localStorage.setItem(key,value);}return value;}
  function date(iso){return new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(iso));}
  function warn(){notify('대화를 브라우저에 보관하지 못했어요. 현재 창의 내용을 복사해 두세요.');}
  function load(author){
    try{
      const version=epoch(author),start=prefix+author+':'+version+':',turns=[];
      for(let i=0;i<localStorage.length;i++){const key=localStorage.key(i);if(!key.startsWith(start))continue;
        try{const t=JSON.parse(localStorage.getItem(key));if(!Array.isArray(t.messages)||!t.messages.length)continue;
          const messages=t.messages.filter(m=>m&&['user','assistant'].includes(m.role)&&typeof m.id==='string'&&typeof m.body==='string'&&Number.isFinite(Date.parse(m.createdAt))).map(m=>({...m,author,day:date(m.createdAt),streaming:false,incomplete:m.incomplete||m.streaming}));
          if(messages[0]?.role==='user')turns.push({id:key,messages:messages.filter(m=>m.role==='user'||m.body.trim()||m.incomplete)});
        }catch{/* A malformed turn must not hide the rest of the archive. */}
      }
      turns.sort((a,b)=>a.messages[0].createdAt.localeCompare(b.messages[0].createdAt)||a.id.localeCompare(b.id));
      const messages=turns.flatMap(t=>t.messages),last=turns.at(-1)?.messages;
      const interrupted=last&&(last.length===1||last[1]?.incomplete);
      return {epoch:version,messages,...(interrupted?{error:'이전 답변이 완료되지 않았어요. 다시 보낼 수 있어요.',failedUser:last[0].id,failedText:last[0].body}:{})};
    }catch{return {epoch:null,messages:[]};}
  }
  function save(author,version,user,assistant){
    try{if(!version||epoch(author)!==version){notify('다른 창에서 대화를 지웠어요. 이번 대화는 현재 창에만 남아요.');return false;}
      localStorage.setItem(prefix+author+':'+version+':'+user.id,JSON.stringify({messages:[user,assistant]}));return true;
    }catch{warn();return false;}
  }
  function clear(author){
    try{const old=epoch(author),start=prefix+author+':'+old+':';localStorage.setItem(prefix+author+':epoch',crypto.randomUUID());const keys=[];for(let i=0;i<localStorage.length;i++){const key=localStorage.key(i);if(key.startsWith(start))keys.push(key);}keys.forEach(k=>localStorage.removeItem(k));return true;}catch{warn();return false;}
  }
  return {load,save,clear,date};
})();
function chatMessagesHTML(session){
  let previous='',html='';
  const divider=day=>`<div class="chat-day-divider" role="separator" aria-label="${esc(dateLabel(day))}"><span>${esc(dateLabel(day))}${day===dayKey()?' · 오늘':''}</span></div>`;
  for(const message of session.messages){const day=message.day||dayKey();if(day!==previous){html+=divider(day);previous=day;}html+=messageHTML(message);}
  if(previous!==dayKey())html+=divider(dayKey());
  return html;
}
