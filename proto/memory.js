/* Separate memory is unavailable in the contest prototype.
 * Existing browser data is left untouched; it is neither read nor sent.
 */
const MEMORY_NOTICE='기억은 별도로 저장되지 않습니다. 정식 서비스를 기다려주세요.';
const ChatMemory=Object.freeze({
  read:()=>({enabled:false,automatic:false,entries:[]}),
  observe:()=>{},
  configure:()=>false,
  save:()=>false,
  remove:()=>false,
  payload:()=>[],
  extract:()=>[]
});
function memorySettings(){dialog('대화 기억',`<p class="prose">${MEMORY_NOTICE}</p>`);}
document.addEventListener('click',e=>{
  const button=e.target.closest('button');
  if(button&&!button.disabled&&button.dataset.action==='memory-settings')memorySettings();
});
