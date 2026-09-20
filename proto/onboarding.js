(() => {
  const key = 'jane-onboarding-v1';
  const disclaimer = '*작가의 작품을 모티브로 만든 가상의 AI 상담사예요.\n실제 작가의 발언, 행적과는 상이합니다.';
  const steps = [
    ['위대한 작가들에게\n나의 고민을.', '관계도, 일도, 나 자신도.\n작가의 작품에서 빌린 시선으로\n지금의 마음을 함께 살펴봐요.', disclaimer],
    ['누구와 이야기할까요?', '오스틴, 윌리엄, 체호프.\n나에게 맞는 시선을 골라보세요.', disclaimer],
    ['너무나 막막할 때는 예언을', '작품 속 문장이\n세 마녀의 예언이 되어 찾아와요.', '생년월일과 태어난 지역을 입력하고,\n오늘의 마음을 비춰볼 한마디를 받아보세요.'],
    ['전하지 못한 마음을', '하루 한 통, 백 자 안에\n미처 전하지 못한 마음을 적어보세요.', '대화하다 떠오른 마음도, 혼자 품었던 마음도.\n‘나의 기록’의 편지함에서 따로 쓸 수 있어요.']
  ];
  let step = 0, previousFocus;
  const layer = document.createElement('section');
  layer.className = 'onboarding'; layer.hidden = true;
  layer.setAttribute('role', 'dialog'); layer.setAttribute('aria-modal', 'true');
  layer.setAttribute('aria-labelledby', 'onboarding-title');
  layer.innerHTML = `<div class="onboarding-stage"><img class="onboarding-image" alt=""><div class="onboarding-dim"></div><div class="onboarding-panel"><div class="onboarding-controls"><span class="onboarding-count"></span><button type="button" class="onboarding-back">이전</button><button type="button" class="onboarding-skip">건너뛰기</button></div><h2 id="onboarding-title" tabindex="-1"></h2><p class="onboarding-body"></p><p class="onboarding-note"></p><button type="button" class="primary onboarding-next">다음</button></div></div>`;
  document.body.append(layer);
  const find = s => layer.querySelector(s);
  function renderStep() {
    const [title, body, note] = steps[step];
    find('.onboarding-image').src = `./assets/onboarding/onboarding-${step + 1}.png`;
    find('.onboarding-count').textContent = `0${step + 1} / 04`;
    find('#onboarding-title').textContent = title;
    find('.onboarding-body').textContent = body;
    find('.onboarding-note').textContent = note;
    find('.onboarding-back').hidden = step === 0;
    find('.onboarding-next').textContent = step === 3 ? '작가와 이야기 시작하기' : '다음';
    find('.onboarding-panel').scrollTop = 0;
    find('#onboarding-title').focus({preventScroll:true});
  }
  function open() {
    if (!layer.hidden) return;
    previousFocus = document.activeElement; step = 0;
    document.querySelector('#dialog')?.close();
    document.querySelector('#app').inert = true;
    layer.hidden = false; renderStep();
  }
  function finish() {
    try { localStorage.setItem(key, 'done'); } catch (_) {}
    layer.hidden = true; document.querySelector('#app').inert = false;
    if (previousFocus?.isConnected) previousFocus.focus({preventScroll:true});
  }
  find('.onboarding-next').addEventListener('click', () => step < 3 ? (step++, renderStep()) : finish());
  find('.onboarding-back').addEventListener('click', () => { if (step > 0) {step--; renderStep();} });
  find('.onboarding-skip').addEventListener('click', finish);
  layer.addEventListener('keydown', e => {
    if (e.key === 'Escape') { e.preventDefault(); finish(); }
    if (e.key !== 'Tab') return;
    const buttons = [...layer.querySelectorAll('button')].filter(b => !b.hidden);
    const first = buttons[0], last = buttons[buttons.length - 1];
    if (e.shiftKey && (document.activeElement === first || document.activeElement.id === 'onboarding-title')) {e.preventDefault(); last.focus();}
    else if (!e.shiftKey && document.activeElement === last) {e.preventDefault(); first.focus();}
  });
  document.addEventListener('click', e => {if(e.target.closest('[data-action="show-onboarding"]')) open();});
  let completed = false; try {completed = localStorage.getItem(key) === 'done';} catch (_) {}
  if (!completed || new URLSearchParams(location.search).get('onboarding') === '1') open();
})();
