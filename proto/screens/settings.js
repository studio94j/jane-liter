"use strict";
// Screen functions share app state; app.js owns initialization and routing.
function profile(id) {
  const a = AUTHORS[id];
  dialog(
    `${a.name}의 시선`,
    `<p class="profile-subtitle">${a.full}의 작품을 바탕으로 만든 가상의 AI 상담사예요.</p><div class="profile-scroll" tabindex="0" role="region" aria-label="${a.name}의 소개"><div class="profile-top"><img src="${a.image}" alt="${a.full}"><div><p class="author-en">${a.en}</p><h3>${a.full}</h3></div></div><p class="prose">${a.description}</p>${a.voice ? `<p class="detail-label">대화의 말투</p><p class="prose">${a.voice}</p>` : ""}${a.principles.map(([t, p], i) => `<section class="principle"><h3>0${i + 1} &nbsp; ${t}</h3><p>${p}</p></section>`).join("")}<p class="detail-label">이 조언가의 책장</p><p class="prose">${a.books.map((b) => `『${BOOKS[b].title}』`).join(" · ")}</p><p class="role-foot">이 성향과 대화는 작품의 인물·갈등·선택에서 빌린 서비스의 해석입니다. 작가의 실제 발언이나 모든 작품의 유일한 해석을 뜻하지 않습니다.</p></div><div class="profile-footer"><button class="primary" data-chat-author="${id}">${a.name}과 이야기 나누기 ${icon("arrow")}</button></div>`,
    "author-profile",
  );
}
function switchDialog() {
  dialog(
    "다른 시선으로 이야기할까요?",
    `<p class="sub">조언가마다 현재 대화를 따로 유지해요.<br>다른 조언가에게 이전 대화가 자동으로 전달되지는 않아요.</p>${Object.values(
      AUTHORS,
    )
      .map(
        (a) =>
          `<button class="switch-row" data-chat-author="${a.id}"><img src="${a.image}" alt=""><span class="switch-copy"><strong>${a.name}</strong><span>${a.role}</span></span>${icon(state.author === a.id ? "check" : "arrow")}</button>`,
      )
      .join("")}`,
  );
}
function chooseAuthor(id) {
  if (!AUTHORS[id]) return;
  state.author = id;
  try {
    localStorage.setItem(prefKey, JSON.stringify({ author: id }));
  } catch {
    notify("현재 창에만 작가 설정을 유지할 수 있어요.");
  }
}
function extraAbout() {
  dialog(
    "Jane · 하루 한 통의 마음",
    `<div class="prose"><p>작가와 고민을 나누고, 미처 말하지 못한 마음을 부치지 않을 편지로 남겨요. 대화하지 않고 편지만 써도 괜찮아요.</p><p class="detail-label">하루 한 통 · 본문 100자 이내</p><p>서울 시간의 날짜를 기준으로 하루 한 통을 보관해요. 같은 날 다시 쓰면 기존 편지를 수정해요. 공백·문장부호·줄바꿈을 포함하며, 한글 조합과 이모지는 화면에 보이는 글자 단위로 셉니다. 받는 마음 표시는 본문 글자 수에 포함하지 않아요.</p><p class="detail-label">작가 설정과 기록</p><p>${RETENTION_NOTICE} 선택한 작가, 대화, 보관한 편지·책·조언·예언은 현재 브라우저에 임시로 저장돼요. 브라우저 데이터 삭제나 이용 환경 및 체험 서비스 변경에 따라 기록이 사라질 수 있어요. 다른 기기와의 동기화나 복구는 제공하지 않아요. 편지는 보관을 눌렀을 때만 저장하며, 작성 중인 글은 현재 창에서만 유지돼요. 대화는 서울 시간 기준 날짜로 구분해요. 공유 기기에서는 다른 사람도 기록을 읽을 수 있어요.</p><p class="detail-label">작품 기반 대화와 세 마녀의 예언</p><p>대화를 보낼 때 최근 대화를 AI 제공사에 전달해 답변을 만들어요. 공개 서비스는 Google Gemini를 사용합니다. 개인정보와 민감한 내용은 입력하지 말아 주세요. 답변과 작품 해석에 오류가 있을 수 있으며 전문적인 위기 대응을 대신할 수 없어요.</p><div class="stack"><button class="secondary danger" data-action="delete-all-letters">보관한 편지 전체 삭제</button></div></div>`,
  );
}
function about() {
  extraAbout();
}
function settingsPage() {
  const a = AUTHORS[state.author];
  return `<div class="screen settings-screen"><h1>설정</h1><p class="sub">고민 이야기를 나눌 작가를 고르고, 기록을 관리해요.</p><section class="settings-section"><div class="section-row"><h2>나의 조언가</h2><span class="settings-saved">${icon("check")} 자동 저장</span></div>${Object.values(
    AUTHORS,
  )
    .map(
      (x) =>
        `<div class="switch-row settings-author ${x.id === a.id ? "selected" : ""}"><button class="author-thumbnail" data-author-thumbnail="${x.id}" aria-label="${x.name} 선택, 두 번 누르거나 길게 눌러 상세 보기" aria-pressed="${x.id === a.id}"><img src="${x.image}" alt="" draggable="false"></button><button class="author-select" data-settings-author="${x.id}" aria-pressed="${x.id === a.id}"><span class="switch-copy"><strong>${x.name}</strong><span>${x.role}</span></span><span class="author-selection-mark">${x.id === a.id ? icon("check") : ""}</span></button><button class="icon-button author-more" data-profile="${x.id}" aria-label="${x.name} 더보기" aria-haspopup="dialog">${icon("more")}</button></div>`,
    )
    .join(
      "",
    )}<p class="sub">선택한 작가와 대화는 현재 브라우저에 임시로 저장돼요.</p></section><section class="settings-section"><h2>대화 기억</h2><p class="sub">${MEMORY_NOTICE}</p></section><section class="settings-section"><h2>기록 관리</h2><div class="settings-info"><span>하루에 남기는 편지</span><strong>한 통 · 본문 100자</strong></div><div class="settings-info"><span>하루의 기준</span><strong>서울 시간 · 자정</strong></div><div class="settings-info"><span>보관된 편지</span><strong>${Object.keys(letters).length}통</strong></div><button class="settings-link" data-action="delete-all-letters"><span>보관한 편지 전체 삭제</span>${icon("right")}</button><p class="sub">${RETENTION_NOTICE}<br>다른 기기와 동기화하거나 복구하는 기능은 제공하지 않아요.</p></section><section class="settings-section"><h2>Jane 안내</h2><button class="settings-link" data-action="show-onboarding"><span>처음 안내 다시 보기</span>${icon("right")}</button><button class="settings-link" data-action="about"><span>서비스와 저장 안내</span>${icon("right")}</button><p class="fine" style="text-align:left">작품 기반 AI 대화</p></section><footer class="settings-contact">서비스 관련 문의 사항은 제작자 이메일<br><a href="mailto:hemingway3988@gmail.com">hemingway3988@gmail.com</a>으로 연락해주세요!</footer></div>`;
}
function openAuthorBooks() {
  const a = AUTHORS[state.author];
  dialog(
    `${a.name}의 작품`,
    `${a.books.map((id) => bookCard(id, BOOKS[id].tag, true)).join("")}`,
  );
}
// Thumbnail single tap selects; double tap / long press opens its profile.
let authorPress = null,
  authorTap = null,
  authorTapTimer,
  authorPressTimer,
  suppressAuthorClickUntil = 0;
function cancelAuthorPress() {
  clearTimeout(authorPressTimer);
  authorPress = null;
}
function openThumbnailProfile(id) {
  clearTimeout(authorTapTimer);
  authorTap = null;
  cancelAuthorPress();
  suppressAuthorClickUntil = Date.now() + 800;
  profile(id);
}
document.addEventListener("pointerdown", (e) => {
  const thumb = e.target.closest("[data-author-thumbnail]");
  if (!thumb || !e.isPrimary || e.button !== 0) return;
  cancelAuthorPress();
  authorPress = {
    id: thumb.dataset.authorThumbnail,
    x: e.clientX,
    y: e.clientY,
    pointer: e.pointerId,
  };
  authorPressTimer = setTimeout(() => {
    if (authorPress) openThumbnailProfile(authorPress.id);
  }, 600);
});
document.addEventListener("pointermove", (e) => {
  if (
    authorPress &&
    e.pointerId === authorPress.pointer &&
    Math.hypot(e.clientX - authorPress.x, e.clientY - authorPress.y) > 10
  )
    cancelAuthorPress();
});
document.addEventListener("pointerup", cancelAuthorPress);
document.addEventListener("pointercancel", cancelAuthorPress);
document.addEventListener("scroll", cancelAuthorPress, true);
window.addEventListener("blur", () => {
  cancelAuthorPress();
  clearTimeout(authorTapTimer);
  authorTap = null;
});
document.addEventListener("contextmenu", (e) => {
  if (e.target.closest("[data-author-thumbnail]")) e.preventDefault();
});
document.addEventListener("click", (e) => {
  const thumb = e.target.closest("[data-author-thumbnail]");
  if (!thumb) return;
  if (Date.now() < suppressAuthorClickUntil) {
    e.preventDefault();
    return;
  }
  const id = thumb.dataset.authorThumbnail;
  if (e.detail === 0) {
    chooseAuthor(id);
    render({ keep: true });
    return;
  }
  if (authorTap?.id === id && Date.now() - authorTap.time < 400) {
    openThumbnailProfile(id);
    return;
  }
  clearTimeout(authorTapTimer);
  authorTap = { id, time: Date.now() };
  authorTapTimer = setTimeout(() => {
    authorTap = null;
    if (state.page === "settings" && !$("#dialog").open) {
      chooseAuthor(id);
      render({ keep: true });
    }
  }, 400);
});
document.addEventListener("dblclick", (e) => {
  const thumb = e.target.closest("[data-author-thumbnail]");
  if (thumb && Date.now() >= suppressAuthorClickUntil)
    openThumbnailProfile(thumb.dataset.authorThumbnail);
});
