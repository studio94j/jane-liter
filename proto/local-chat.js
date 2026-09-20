'use strict';
const localModel = {status:'checking', name:'AI', provider:'', label:''};
const requests = new Map();

function connectionLabel(){return localModel.status==='ready'?(localModel.label||localModel.name):localModel.status==='offline'?'대화 연결 확인 필요':'대화 연결 확인 중';}
async function checkLocalModel(){
  try{const r=await fetch('/api/health',{signal:AbortSignal.timeout(5000)});const data=await r.json();localModel.status=r.ok&&data.ready?'ready':'offline';localModel.provider=data.provider||'ollama';localModel.name=data.model||'AI';localModel.label=data.label||(data.model+' · 로컬 AI');}
  catch{localModel.status='offline';}
  const el=document.querySelector('#model-status');if(el)el.textContent=connectionLabel();
}
function chatRequestHistory(session, latest){
  const complete=[];
  for(let i=0;i<session.messages.length-1;i++){
    const u=session.messages[i],a=session.messages[i+1];
    if(u.role==='user'&&a.role==='assistant'&&!a.streaming&&!a.incomplete&&a.body){
      complete.push({role:'user',content:u.body},{role:'assistant',content:a.body+(a.question?'\n'+a.question:'')});i++;
    }
  }
  return [...complete.slice(-40),{role:'user',content:latest}];
}
function localErrorHTML(session){return session.error?`<div class="local-error" role="alert"><p>${esc(session.error)}</p><button class="text-button" data-action="retry-local">다시 보내기 ${icon('arrow')}</button></div>`:'';}
function quotationHTML(message){
  if(message.retrieval?.status==='safety-priority')return '';
  const q=message.quotation;
  if(!q)return '';
  return `<figure class="literary-quotation"><p class="quote-label">${q.text_kind==='translation-en'?'영문 번역판에서':'영어 원문에서'}</p><blockquote lang="en">${esc(q.english)}</blockquote><p class="quote-korean" lang="ko">${q.translation_status==='complete'?esc(q.korean):'한국어 번역을 완료하지 못했어요. 영어 발췌는 원문과 확인했어요.'}</p><figcaption>『${esc(q.title)}』 · ${esc(q.section)}${q.text_kind==='translation-en'&&q.translator&&!q.translator.startsWith('Not stated')?'<br>영문 번역 · '+esc(q.translator):''}</figcaption></figure>`;
}
function sourceLinkHTML(message){
  if(message.streaming)return '';
  const sources=message.sources||(message.source?[message.source]:[]);
  if(sources.length)return `<button class="text-button source-link" data-source="${message.id}">${icon('book')} 참고한 ${esc(({austen:'제인 오스틴',william:'셰익스피어',chekhov:'체호프'})[message.author]||AUTHORS[state.author].full)}의 작품</button>`;
  if(message.retrieval?.status==='scope-guidance')return '';
  return '';
}
function showSource(id){
  const message=sessions[state.author].messages.find(x=>x.id===id);
  const sources=message?.sources||(message?.source?[message.source]:[]);
  if(!sources.length)return;
  const intro=message.retrieval?`저장된 ${Number(message.retrieval.corpus.works)}작품 전체에서 검색해, 아래 구절을 모델에 전달했어요. 답변이 이 구절을 정확히 해석했다는 보증은 아니에요.`:'이전 대화에 전달했던 고정 발췌문이에요.';
  dialog(`참고한 ${({austen:'제인 오스틴',william:'셰익스피어',chekhov:'체호프'})[message.author]||AUTHORS[state.author].full}의 작품`,`<p class="sub">${intro}</p>${sources.map(source=>`<section class="source-section"><p class="detail-label">${esc(source.display_title||source.title)}</p><p class="fine">${esc(source.section||'')}</p><p class="source-excerpt">${esc(source.text)}</p><p class="fine">Project Gutenberg${source.text_kind==='translation-en'?' · 영문 번역판 (러시아어 원작)':''}${source.translator&&source.translator!=='Not stated in the downloaded edition'?' · '+esc(source.translator):''}</p></section>`).join('')}<p class="fine">전체 원문을 매번 입력하는 대신, 고민과 관련된 부분만 전달해요. 작품마다 같은 비율로 선택하지는 않아요.</p>`);
}

async function send(text,kind,retry=false){
  text=String(text||'').trim();const author=state.author,s=sessions[author];
  if(!text||s.pending)return;
  if(text.length>2000){notify('한 번에 2,000자까지 이야기할 수 있어요.');return;}
  const retryUser=retry?s.messages.find(m=>m.id===s.failedUser):null;
  if(!s.archiveUnsaved){const saved=ChatArchive.load(author);s.messages=saved.messages;s.epoch=saved.epoch;}
  if(retry&&s.failedUser){s.messages=s.messages.filter(m=>m.id!==s.failedUser&&!m.incomplete);}
  s.error='';s.failedUser=null;s.failedText='';s.draft='';
  const history=chatRequestHistory(s,text);
  const createdAt=retryUser?.createdAt||new Date().toISOString();
  const user={id:retryUser?.id||cryptoId(),role:'user',body:text,createdAt,day:ChatArchive.date(createdAt)};
  if(!retry)ChatMemory.observe(author,text);
  const message={id:cryptoId(),role:'assistant',author,body:'',streaming:true,createdAt,day:user.day};
  s.messages.push(user,message);s.archiveUnsaved=!ChatArchive.save(author,s.epoch,user,message);s.pending=true;s.loadingStage='reading';s.loadingStarted=Date.now();
  const controller=new AbortController();requests.set(author,controller);
  let timedOut=false,finished=false,buffer='',receivedText=false,limitNotice=false;
  let timer;function resetTimer(){clearTimeout(timer);timer=setTimeout(()=>{timedOut=true;controller.abort();},180000);}resetTimer();
  const loadingTimer=setInterval(()=>{if(s.loadingStage==='reading')setLoadingStage('reading');},1000);
  render({bottom:true});
  function update(){
    if(state.page!=='chat'||state.author!==author)return;
    const thread=$('#thread'),nearBottom=thread&&thread.scrollHeight-thread.scrollTop-thread.clientHeight<100;
    const body=document.querySelector(`[data-message="${message.id}"] .message-body`);
    if(body)body.textContent=message.body;
    if(receivedText&&s.loadingStage==='reading')setLoadingStage('writing');
    if(nearBottom)scrollChat();
  }
  function setLoadingStage(stage){
    s.loadingStage=stage;
    if(state.page!=='chat'||state.author!==author)return;
    const text=loadingStatus(author,stage);
    document.querySelectorAll('.loading-status, [data-loading-status]').forEach(el=>{el.textContent=text;el.hidden=stage==='writing';});
    const loading=document.querySelector('.literary-loading');if(loading)loading.hidden=stage==='writing';
  }
  function consume(line){
    if(!line.trim())return;resetTimer();const event=JSON.parse(line);
    if(event.type==='meta'){message.sources=event.sources;message.source=event.source;message.retrieval=event.retrieval;message.contextTrimmed=event.trimmed;}
    if(event.type==='status'&&event.stage==='quotation')setLoadingStage('quotation');
    if(event.type==='quote'){message.quotation=event.quote;message.quotationChecked=true;}
    if(event.type==='replace'){message.body=event.content;receivedText=!!message.body;update();}
    if(event.type==='delta'){message.body+=event.content;receivedText=true;update();}
    if(event.type==='error')throw new Error(event.message);
    if(event.type==='done'){finished=true;message.limited=event.reason==='length';}
  }
  try{
    if(typeof cloudSessionReady!=='undefined')await cloudSessionReady;
    if(window.janeConnectionError)throw new Error(window.janeConnectionError);
    const response=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':user.id+'-'+message.id},body:JSON.stringify({author,messages:history,memory:ChatMemory.payload(author),situation:s.situation||null}),signal:controller.signal});
    if(!response.ok){let error;try{error=await response.json();}catch{}limitNotice=response.status===429&&['limit_day','limit_budget'].includes(error?.code);throw new Error(error?.error||'대화 서버에 연결할 수 없어요. 실행 안내를 확인해 주세요.');}
    if(!response.body)throw new Error('스트리밍 연결을 열 수 없어요.');
    localModel.status='ready';
    const reader=response.body.getReader(),decoder=new TextDecoder();
    while(true){
      const {done,value}=await reader.read();
      if(done){buffer+=decoder.decode();break;}
      buffer+=decoder.decode(value,{stream:true});
      let newline;while((newline=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,newline);buffer=buffer.slice(newline+1);consume(line);}
    }
    if(buffer.trim())consume(buffer);
    if(!finished||!message.body.trim())throw new Error('답변이 끝나기 전에 연결이 끊겼어요. 다시 시도해 주세요.');
  }catch(error){
    controller.abort();message.incomplete=true;
    s.failedUser=user.id;s.failedText=text;
    s.error=timedOut?'답변 대기 시간이 초과됐어요. 잠시 뒤 다시 보내 주세요.':error.name==='AbortError'?'답변 생성을 중단했어요.':error.message==='Failed to fetch'?'대화 서버에 연결할 수 없어요. 잠시 뒤 다시 시도해 주세요.':error.message;
    if(!message.body.trim())s.messages=s.messages.filter(m=>m.id!==message.id);
  }finally{
    clearTimeout(timer);clearInterval(loadingTimer);requests.delete(author);message.streaming=false;s.pending=false;s.loadingStage=null;
    s.archiveUnsaved=!ChatArchive.save(author,s.epoch,user,message);
    if(finished&&!message.incomplete){s.letterSuggestionDay=dayKey();if(typeof markProphecyConversationStarted==='function')markProphecyConversationStarted();}
    if(typeof syncFortuneControls==='function')syncFortuneControls();
    if(state.page==='chat'&&state.author===author)render({keep:true});
    if(limitNotice)showUsageLimitNotice();
  }
}
document.addEventListener('click',event=>{
  const button=event.target.closest('button');if(!button||button.disabled)return;
  if(button.dataset.action==='stop-local')requests.get(state.author)?.abort();
  if(button.dataset.action==='retry-local')send(sessions[state.author].failedText,null,true);
  if(button.dataset.action==='check-local')checkLocalModel();
  if(button.dataset.source)showSource(button.dataset.source);
});
window.addEventListener('DOMContentLoaded',checkLocalModel);

function showUsageLimitNotice(){
  dialog('대화 이용 한도에 도달했어요',`<div class="prose"><p>심사 등의 이유로 일일 이용 한도 해제가 필요하다면 제작자에게 연락해 주세요.</p><p><a href="mailto:hemingway3988@gmail.com?subject=Jane%20이용%20한도%20해제%20문의">hemingway3988@gmail.com</a></p><p class="sub">문의 내용을 확인한 후 안내해 드릴게요.</p></div>`);
}
