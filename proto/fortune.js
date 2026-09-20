'use strict';
// Source excerpts are randomly drawn from all three authors by the local server.
let prophecyPending=false,prophecyError='',prophecyRequest=0,prophecyController=null;
let prophecySeen=[];
// Birth details live only in this page's memory, never in storage or model requests.
let prophecyBirthDraft={dob:'',region:''};
let prophecyProfile=null;
let prophecyReading=null;
let activeFortune=null;
function normalizeBirthRegion(value){return String(value||'').normalize('NFC').trim().replace(/\s+/gu,' ');}
function validateProphecyProfile(dob,region,today=dayKey()){
 const place=normalizeBirthRegion(region),match=/^(\d{4})-(\d{2})-(\d{2})$/.exec(dob||'');
 if(!match)return {field:'dob',error:'태어난 날짜를 입력해 주세요.'};
 const [,y,m,d]=match.map(Number),date=new Date(Date.UTC(y,m-1,d));
 if(y<1900||date.getUTCFullYear()!==y||date.getUTCMonth()!==m-1||date.getUTCDate()!==d||dob>today)return {field:'dob',error:'1900년부터 오늘까지의 실제 날짜를 입력해 주세요.'};
 if([...place].length<2||[...place].length>60||!/[\p{L}]/u.test(place)||!/^[\p{L}\p{M} .,'’()·/\-]+$/u.test(place))return {field:'region',error:'태어난 도시나 지역을 2~60자로 입력해 주세요. 예: 서울, London'};
 return {profile:{dob,region:place}};
}
function prophecyProfileKey(profile){return profile.dob+'|'+profile.region.toLocaleLowerCase('en-US');}
function dailyProphecy(date){
 if(!prophecyProfile||prophecyReading?.date!==date||prophecyReading?.key!==prophecyProfileKey(prophecyProfile))return null;
 const card=prophecyReading.card;if(!card)return null;
 const [,month,birthDay]=prophecyProfile.dob.split('-').map(Number);
 return {...card,lines:[`${prophecyProfile.region}에서 ${month}월 ${birthDay}일에 태어난 자여. ${card.lines[0]}`,...card.lines.slice(1)]};
}
function witchesScene(){return `<img class="witches-scene" src="./assets/prophecy/three-witches-hamsters-v1.png" width="1254" height="1254" alt="가마솥을 둘러싸고 예언하는 세 마녀 햄스터">`;}
function openFortune(author=state.author,editing=false){
 const date=dayKey();activeFortune={author,date};
 const a=AUTHORS[author],opened=prophecyProfile&&prophecyReading?.date===date&&prophecyReading?.key===prophecyProfileKey(prophecyProfile);
 const intro=`<p class="fortune-meta">${esc(dateLabel(date))}<span>세 작가의 작품 · 세 마녀</span></p>`;
 if(prophecyPending){
  dialog('세 마녀의 예언',`<section class="fortune-view prophecy-birth" data-prophecy-loading>${intro}${witchesScene()}<p class="fortune-invite" role="status">세 마녀가 작품 속에서<br>그대의 징조를 읽고 있어요.</p><p class="fortune-fine prophecy-caption">세 목소리가 들려줄 이야기를 기다려 주세요.</p></section>`);return;
 }
 const error=prophecyError?`<p class="prophecy-form-error" role="alert">${esc(prophecyError)}</p>`:'';
 if(editing||!opened){
  dialog('세 마녀의 예언',`<section class="fortune-view prophecy-invitation prophecy-birth">${intro}<p class="prophecy-eyebrow">그대가 처음 세상에 온 날과 곳을 말하라.</p>${witchesScene()}<form id="prophecy-birth-form" novalidate autocomplete="off"><div class="prophecy-field"><label for="prophecy-dob">생년월일 <small>양력</small></label><input id="prophecy-dob" name="dob" type="date" min="1900-01-01" max="${date}" required value="${esc(prophecyBirthDraft.dob)}" aria-describedby="prophecy-form-error"></div><div class="prophecy-field"><label for="prophecy-region">태어난 지역</label><input id="prophecy-region" name="region" type="text" maxlength="60" required value="${esc(prophecyBirthDraft.region)}" placeholder="도시 또는 지역 · 예: 서울, London" aria-describedby="prophecy-form-error"></div><p id="prophecy-form-error" class="prophecy-form-error" role="alert">${esc(prophecyError)}</p><button class="primary prophecy-listen" type="submit">나의 예언 듣기 ${icon('arrow')}</button></form><p class="fortune-fine prophecy-caption">세 작가의 작품에서 무작위로 뽑은 구절을 예언으로 엮어요.<br>입력 정보는 이 창에서만 유지되며, 새로고침하면 지워져요.</p>${opened?'<button class="text-button prophecy-edit" data-action="prophecy-cancel-edit">이전 예언으로 돌아가기</button>':''}${prophecyProfile?'<button class="text-button prophecy-edit" data-action="clear-prophecy-profile">입력 정보 지우기</button>':''}</section>`);
 }else{
  const card=dailyProphecy(date),q=card.quote;
  dialog('세 마녀의 예언',`<section class="fortune-view fortune-revealed">${intro}${error}<div class="prophecy-birth-summary"><p>${esc(prophecyProfile.dob.replaceAll('-','.'))} · ${esc(prophecyProfile.region)}</p><button class="text-button" data-action="edit-prophecy-profile">정보 수정</button></div><div class="fortune-paper"><p class="fortune-kind">그대를 위한 오늘의 징조</p><h3>${esc(card.title)}</h3><p class="prophecy-label">원문에서 빌린 마녀의 말 · 창작</p><ol class="witch-voices">${card.lines.map((line,i)=>`<li style="--voice-index:${i}"><span>${['첫째','둘째','셋째'][i]} 마녀</span><p>${esc(line)}</p></li>`).join('')}</ol><div class="fortune-action"><span>예언을 오늘의 선택으로</span><p>${esc(card.action)}</p></div></div><details class="fortune-source"><summary>『${esc(q.title)}』의 원문 ${icon('book')}</summary><blockquote lang="ko">${esc(q.korean)}</blockquote><p class="fortune-english" lang="en">${esc(q.english)}</p><p class="fortune-fine">${esc(q.author_name)} · 『${esc(q.title)}』 · ${esc(q.section)}${q.text_kind==='translation-en'?' · 영문 번역판':''}</p></details><p class="fortune-fine fortune-context">사주·점성술 계산이나 실제 미래 예측은 아니에요.</p><button class="primary" data-action="fortune-chat" ${sessions[author].pending?'disabled':''}>${sessions[author].pending?'답변을 받은 뒤 해석 나누기':esc(a.name)+'과 해석 나누기'} ${icon('arrow')}</button><button class="secondary prophecy-again" data-action="reroll-prophecy">예언 다시 받기 ↻</button><p class="fortune-fine prophecy-caption">예언은 이 브라우저의 ‘나의 기록 → 예언’에 임시로 저장돼요. 생년월일과 지역은 저장하지 않아요.<br>${RETENTION_NOTICE}</p><button class="text-button prophecy-edit" data-action="clear-prophecy-profile">입력 정보 지우기</button></section>`);
 }
}
function revealFortune(){
 if(!activeFortune)return;
 const dob=document.querySelector('#prophecy-dob')?.value||'',region=document.querySelector('#prophecy-region')?.value||'';
 prophecyBirthDraft={dob,region};
 const result=validateProphecyProfile(dob,region);
 document.querySelectorAll('#prophecy-birth-form input').forEach(input=>input.removeAttribute('aria-invalid'));
 if(result.error){const error=document.querySelector('#prophecy-form-error');if(error)error.textContent=result.error;const input=document.querySelector('#prophecy-'+result.field);input?.setAttribute('aria-invalid','true');input?.focus();return;}
 prophecyProfile=result.profile;prophecyBirthDraft={...prophecyProfile};
 const date=dayKey(),key=prophecyProfileKey(prophecyProfile);
 if(prophecyReading?.date===date&&prophecyReading?.key===key){prophecyError='';openFortune(activeFortune.author);return;}
 requestProphecy();
}
async function requestProphecy(fromArchive=false){
 if(!activeFortune||(!fromArchive&&!prophecyProfile)||prophecyPending)return;
 const date=dayKey(),key=fromArchive?null:prophecyProfileKey(prophecyProfile),token=++prophecyRequest;
 let archived=null;const requestAuthor=activeFortune.author;
 prophecyPending=true;prophecyError='';const controller=new AbortController();prophecyController=controller;
 const timer=setTimeout(()=>controller.abort(),170000);
 openFortune(activeFortune.author);
 try{
  if(typeof cloudSessionReady!=='undefined')await cloudSessionReady;
  const response=await fetch('/api/prophecy',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({exclude:prophecySeen.slice(-20)}),signal:controller.signal});
  const data=await response.json();
  if(!response.ok)throw new Error(data.error||'예언을 받지 못했어요. 다시 시도해 주세요.');
  if(!data.card||!Array.isArray(data.card.lines)||data.card.lines.length!==3||!data.card.quote?.english)throw new Error('예언을 완성하지 못했어요. 다시 받아 주세요.');
  if(token!==prophecyRequest||(!fromArchive&&(!prophecyProfile||key!==prophecyProfileKey(prophecyProfile)||date!==dayKey())))return;
  archived=ProphecyArchive.save(data.card,requestAuthor);
  if(!fromArchive)prophecyReading={date,key,card:data.card};prophecySeen=[...prophecySeen,data.card.id].slice(-20);
 }catch(error){if(token===prophecyRequest)prophecyError=error.name==='AbortError'?'예언을 기다리는 시간이 길어졌어요. 다시 시도해 주세요.':error.message;}
 finally{
  clearTimeout(timer);
  if(token===prophecyRequest){
   prophecyPending=false;prophecyController=null;
   if(state.page==='records'&&state.recordView==='prophecies')render({keep:true});
   if(document.querySelector('#dialog[open] [data-prophecy-loading]')){
    if(fromArchive){if(archived)viewArchivedProphecy(archived.id);else dialog('예언을 보관하지 못했어요.',`<p class="prose">${esc(prophecyError||'저장 공간을 확인한 뒤 다시 받아 주세요.')}</p><button class="secondary" data-action="close">닫기</button>`);}
    else openFortune(activeFortune.author);
    const heading=document.querySelector('.fortune-paper h3');heading?.setAttribute('tabindex','-1');heading?.focus({preventScroll:true});
    document.querySelector('#dialog')?.scrollTo({top:0,behavior:'instant'});
   }
  }
 }
}
function rerollProphecy(){
 if(!activeFortune||prophecyPending)return;
 const {author}=activeFortune,date=dayKey();
 if(!prophecyProfile||activeFortune.date!==date||prophecyReading?.date!==date||prophecyReading?.key!==prophecyProfileKey(prophecyProfile)){openFortune(author);return;}
 requestProphecy();
}
function clearProphecyProfile(){prophecyRequest++;prophecyController?.abort();prophecyController=null;prophecyPending=false;prophecyError='';prophecyProfile=null;prophecyReading=null;prophecyBirthDraft={dob:'',region:''};if(activeFortune)openFortune(activeFortune.author);}
function fortuneToChat(){
 if(!activeFortune||prophecyPending)return;
 const {author}=activeFortune,date=dayKey();
 if(!prophecyProfile||activeFortune.date!==date||prophecyReading?.date!==date||prophecyReading?.key!==prophecyProfileKey(prophecyProfile)){openFortune(author);return;}
 if(sessions[author].pending)return;
 const card=dailyProphecy(date);
 const prompt=`오늘 ‘세 마녀의 예언’에서 ${card.quote.author_name}의 『${card.quote.title}』 구절을 바탕으로 한 “${card.baseLines.join(' ')}”라는 창작 문구를 읽었어요. 이 예언을 당신의 작품 관점으로 해석하며 제 고민을 이야기해 보고 싶어요.`;
 const s=sessions[author],draft=s.draft.trim()?s.draft+'\n'+prompt:prompt;
 if(draft.length>2000){notify('작성 중인 내용을 조금 줄인 뒤 다시 이어 주세요.');return;}
 s.draft=draft;
 go('chat');const input=document.querySelector('#chat-input');input?.focus();
 if(input){input.selectionStart=input.selectionEnd=input.value.length;}
}
function syncFortuneControls(){
 const button=document.querySelector('[data-action="fortune-chat"]');
 if(!button||!activeFortune)return;
 const pending=sessions[activeFortune.author].pending;
 button.disabled=pending;
 button.innerHTML=(pending?'답변을 받은 뒤 해석 나누기':esc(AUTHORS[activeFortune.author].name)+'과 해석 나누기')+' '+icon('arrow');
}
document.addEventListener('click',event=>{
 const button=event.target.closest('button');if(!button||button.disabled)return;
 if(button.dataset.action==='open-fortune')openFortune();
 if(button.dataset.action==='edit-prophecy-profile')openFortune(activeFortune.author,true);
 if(button.dataset.action==='prophecy-cancel-edit')openFortune(activeFortune.author);
 if(button.dataset.action==='clear-prophecy-profile')clearProphecyProfile();
 if(button.dataset.action==='fortune-chat')fortuneToChat();
 if(button.dataset.action==='reroll-prophecy')rerollProphecy();
});

document.addEventListener('submit',event=>{if(event.target.id==='prophecy-birth-form'){event.preventDefault();revealFortune();}});
document.addEventListener('input',event=>{
 if(event.target.id==='prophecy-dob')prophecyBirthDraft.dob=event.target.value;
 if(event.target.id==='prophecy-region')prophecyBirthDraft.region=event.target.value;
 if(['prophecy-dob','prophecy-region'].includes(event.target.id)){event.target.removeAttribute('aria-invalid');const error=document.querySelector('#prophecy-form-error');if(error)error.textContent='';}
});
