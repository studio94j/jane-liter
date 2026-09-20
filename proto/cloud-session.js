'use strict';
// Server-signed anonymous cookie. No signup and no personal data in this request.
const cloudSessionReady=(async()=>{
  const health=await fetch('/api/health').then(r=>r.json()).catch(()=>null);
  if(health?.provider!=='gemini')return;
  const session=await fetch('/api/session');
  if(!session.ok)throw new Error('대화 연결을 준비 중이에요. 잠시 뒤 다시 찾아 주세요.');
  // Old invitation bookmarks now open the same public conversation.
  if(new URLSearchParams(location.hash.slice(1)).has('invite')){
    history.replaceState(null,'',location.pathname+location.search+'#chat');
  }
})().catch(error=>{window.janeConnectionError=error.message;});
