function recordedConversations(){
 const groups=[];
 for(const author of Object.keys(AUTHORS)){
  const session=sessions[author],messages=session.pending||session.archiveUnsaved?session.messages:ChatArchive.load(author).messages;
  const days=new Map();
  for(const m of messages){if(!m.createdAt)continue;const day=m.day||ChatArchive.date(m.createdAt);if(!days.has(day))days.set(day,[]);days.get(day).push(m);}
  for(const [day,items] of days)groups.push({author,day,messages:items,last:items.at(-1).createdAt});
 }
 return groups.sort((a,b)=>b.day.localeCompare(a.day)||b.last.localeCompare(a.last));
}
function conversationRecordsPage(){
 const groups=recordedConversations();
 return `<div class="screen conversation-records"><p class="eyebrow">OUR CONVERSATIONS</p><h1>대화 기록</h1><p class="sub">작가와 나눈 이야기, 마음에 남은 책과 조언.</p><p class="fine">${RETENTION_NOTICE}</p><section class="record-conversations"><div class="section-row"><h2>날짜별 대화</h2><span class="fine">${groups.length}개의 이야기</span></div>${groups.length?groups.map(g=>`<button class="conversation-record-row" data-conversation-day="${g.day}" data-conversation-author="${g.author}"><span class="conversation-record-meta">${esc(dateLabel(g.day))} · ${esc(AUTHORS[g.author].name)}</span><p>${esc(g.messages.find(m=>m.role==='user')?.body||'작가와 나눈 이야기')}</p><small>내가 보낸 이야기 ${g.messages.filter(m=>m.role==='user').length}개 ${icon('right')}</small></button>`).join(''):'<p class="sub record-empty">아직 보관된 대화가 없어요. 이 브라우저에 임시 저장된 대화가 날짜별로 모여요.</p><button class="text-button" data-page="chat">대화 시작하기 →</button>'}</section><section class="record-kept"><h2>저장한 책과 조언</h2>${savedContent()}</section></div>`;
}
function viewConversationDay(author,day){
 const group=recordedConversations().find(g=>g.author===author&&g.day===day);
 if(!group){notify('보관된 대화를 찾을 수 없어요.');return;}
 dialog(`${AUTHORS[author].name}과의 대화`,`<p class="sub">${esc(dateLabel(day))}</p><div class="archived-conversation">${group.messages.map(m=>`<article class="archived-message ${m.role==='user'?'archived-user':''}"><p class="detail-label">${m.role==='user'?'나':esc(AUTHORS[author].name)}</p><p class="archived-body">${esc(m.body)}</p>${m.question?`<p>${esc(m.question)}</p>`:''}${m.role==='assistant'?quotationHTML(m):''}${m.incomplete||m.streaming?'<p class="fine">완료되지 않은 답변</p>':''}</article>`).join('')}</div><button class="primary" data-resume-author="${author}">이 작가와 대화 이어가기 ${icon('arrow')}</button>`);
}
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b||b.disabled)return;if(b.dataset.conversationDay)viewConversationDay(b.dataset.conversationAuthor,b.dataset.conversationDay);if(b.dataset.resumeAuthor){const author=b.dataset.resumeAuthor;if(!AUTHORS[author])return;const s=sessions[author];if(!s.pending&&!s.archiveUnsaved){const archived=ChatArchive.load(author);s.messages=archived.messages;s.epoch=archived.epoch;s.error=archived.error||'';s.failedUser=archived.failedUser||null;s.failedText=archived.failedText||'';}chooseAuthor(author);go('chat');}});
