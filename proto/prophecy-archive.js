/* Keep generated readings, never birth dates or birthplace/personally addressed lines. */
const ProphecyArchive=(()=>{
 const prefix='jane-prophecy-v1:',temporary=new Map();
 function valid(entry){return entry&&typeof entry.id==='string'&&Number.isFinite(Date.parse(entry.createdAt))&&Array.isArray(entry.card?.lines)&&entry.card.lines.length===3&&entry.card.lines.every(x=>typeof x==='string')&&typeof entry.card.title==='string'&&typeof entry.card.action==='string'&&typeof entry.card.quote?.english==='string';}
 function list(){const entries=[...temporary.values()];try{for(let i=0;i<localStorage.length;i++){const key=localStorage.key(i);if(!key?.startsWith(prefix))continue;try{const entry=JSON.parse(localStorage.getItem(key));if(valid(entry))entries.push(entry);}catch{}}}catch{}return entries.sort((a,b)=>b.createdAt.localeCompare(a.createdAt));}
 function save(card,author){
  const quote={};for(const key of ['title','author_name','section','english','korean','text_kind','translator','source_page'])if(typeof card.quote?.[key]==='string')quote[key]=card.quote[key];
  const entry={id:crypto.randomUUID(),createdAt:new Date().toISOString(),date:dayKey(),author,card:{id:card.id,title:card.title,lines:[...card.lines],action:card.action,quote}};
  if(!valid(entry))return null;
  try{localStorage.setItem(prefix+entry.id,JSON.stringify(entry));return entry;}catch{entry.unsaved=true;temporary.set(entry.id,entry);notify('예언을 보관하지 못했어요. 현재 창에만 유지됩니다.');return entry;}
 }
 function remove(id){try{localStorage.removeItem(prefix+id);temporary.delete(id);return true;}catch{notify('예언을 삭제하지 못했어요.');return false;}}
 return {list,save,remove};
})();
function prophecyArchivePage(){
 const entries=ProphecyArchive.list();let previous='';
 return `<div class="screen"><p class="eyebrow">THE WORDS WE KEPT</p><h1>받아 둔 예언</h1><p class="sub">세 마녀가 건넨 말을 날짜별로 다시 살펴보세요.</p>${entries.length?'<button class="secondary" data-action="open-fortune">오늘의 예언 받기</button>':''}${entries.length?entries.map(entry=>{const heading=previous!==entry.date?`<h2 class="archive-day">${esc(dateLabel(entry.date))}</h2>`:'';previous=entry.date;return `${heading}<article class="prophecy-archive-row"><button class="prophecy-archive-open" data-prophecy-entry="${esc(entry.id)}"><small>${esc(entry.card.quote.author_name)} · ${esc(entry.card.quote.title)}</small><strong>${esc(entry.card.title)}</strong><p>${esc(entry.card.lines[0])}</p></button><div class="archive-actions"><button class="text-button" data-prophecy-entry="${esc(entry.id)}">상세 보기</button><button class="text-button" data-prophecy-reroll="${esc(entry.id)}">다시 받기</button><button class="text-button" data-prophecy-delete="${esc(entry.id)}">삭제</button></div></article>`;}).join(''):'<div class="empty"><h2>아직 받아 둔 예언이 없어요.</h2><p>받은 예언은 이 브라우저에 임시로 보관돼요.</p><button class="secondary" data-action="open-fortune">세 마녀의 예언 받기</button></div>'}<p class="fine">${RETENTION_NOTICE}<br>예언과 작품 구절만 임시로 저장해요. 생년월일·태어난 지역은 저장하지 않아요.</p></div>`;
}
function viewArchivedProphecy(id){const entry=ProphecyArchive.list().find(x=>x.id===id);if(!entry){notify('삭제되었거나 찾을 수 없는 예언이에요.');return;}const c=entry.card,q=c.quote;dialog('예언 상세',`<p class="sub">${esc(dateLabel(entry.date))}${entry.unsaved?' · 저장 실패: 현재 창에만 유지':''}</p><div class="fortune-paper"><h3>${esc(c.title)}</h3><p class="fine">작품에서 빌린 마녀의 말 · 창작</p><ol class="witch-voices">${c.lines.map((line,i)=>`<li><span>${['첫째','둘째','셋째'][i]} 마녀</span><p>${esc(line)}</p></li>`).join('')}</ol><div class="fortune-action"><span>예언을 오늘의 선택으로</span><p>${esc(c.action)}</p></div></div><details class="fortune-source"><summary>『${esc(q.title)}』의 원문</summary><blockquote>${esc(q.korean||'')}</blockquote><p lang="en">${esc(q.english)}</p><p class="fine">${esc(q.author_name)} · ${esc(q.section)}</p></details><p class="fine">문학적 해석이며 실제 미래 예측은 아니에요.</p><div class="stack"><button class="secondary" data-prophecy-reroll="${esc(id)}">예언 다시 받기</button><button class="text-button" data-prophecy-delete="${esc(id)}">이 예언 삭제</button></div>`);}
function rerollArchivedProphecy(id){const entry=ProphecyArchive.list().find(x=>x.id===id);if(!entry)return;activeFortune={author:AUTHORS[entry.author]?entry.author:state.author,date:dayKey()};if(entry.card.id)prophecySeen=[...prophecySeen,entry.card.id].slice(-20);requestProphecy(true);}
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b||b.disabled)return;
 if(b.dataset.prophecyEntry)viewArchivedProphecy(b.dataset.prophecyEntry);
 if(b.dataset.prophecyReroll)rerollArchivedProphecy(b.dataset.prophecyReroll);
 if(b.dataset.prophecyDelete)dialog('이 예언을 삭제할까요?',`<p class="prose">보관한 예언 한 건을 삭제합니다. 되돌릴 수 없어요.</p><div class="stack"><button class="primary" data-prophecy-confirm-delete="${esc(b.dataset.prophecyDelete)}">삭제하기</button><button class="secondary" data-action="close">취소</button></div>`);
 if(b.dataset.prophecyConfirmDelete&&ProphecyArchive.remove(b.dataset.prophecyConfirmDelete)){closeDialog();if(state.page==='records')render({keep:true});notify('예언을 삭제했어요.');}
});
