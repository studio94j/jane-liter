let romanceCases=[];
fetch('./situations.json').then(r=>r.json()).then(data=>{romanceCases=data;if(state.page==='chat')render({keep:true});}).catch(()=>{});
function situationSuggestions(){
 const s=sessions[state.author],item=romanceCases.find(x=>x.id===s.situation);
 const lenses={austen:'서로 기대한 것과 실제로 한 말을 함께 살펴보고 싶어요.',william:'제가 바라는 것과 두려워하는 것을 구분하고 싶어요.',chekhov:'말과 마음이 다르네요. 어디서부터 어긋난 걸까요?'};
 const memories=ChatMemory.payload(state.author),past=memories.at(-1);
 return `<section class="situation-start"><button class="text-button" data-situation-open>${item?'이야기 주제 · '+esc(item.label):'어떤 고민이 있나요?'} ${icon('right')}</button>${item?`<button class="starter" data-situation-draft="${esc(item.prompt)}">${esc(item.prompt)}</button>${item.alternative?`<button class="starter" data-situation-draft="${esc(item.alternative)}">${esc(item.alternative)}</button>`:''}<button class="starter" data-situation-draft="${esc(lenses[state.author])}">${esc(lenses[state.author])}</button>`:''}${past?`<button class="starter" data-situation-draft="${esc('전에 “'+past+'”라고 이야기했어요. 지금의 마음을 이어서 이야기하고 싶어요.')}"><small>지난 이야기 이어가기</small><br>${esc(past)}</button>`:''}</section>`;
}
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b||b.disabled)return;
 if('situationOpen'in b.dataset)dialog('오늘의 고민',`<div class="situation-chips" role="group" aria-label="고민 주제">${romanceCases.filter(x=>!x.legacy).map(x=>`<button class="situation-chip" data-situation="${x.id}" aria-pressed="${sessions[state.author].situation===x.id}">${esc(x.label)}</button>`).join('')}</div><div class="situation-reset-row"><button class="situation-reset" data-situation="" ${sessions[state.author].situation?'':'disabled'}>전체 선택 해제</button></div>`);
 if('situation'in b.dataset){sessions[state.author].situation=b.dataset.situation;closeDialog();render({keep:true});}
 if('situationDraft'in b.dataset){const s=sessions[state.author];if(s.pending)return;s.draft=b.dataset.situationDraft;render({keep:true});document.querySelector('#chat-input').focus();}
});
