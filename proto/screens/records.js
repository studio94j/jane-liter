"use strict";
// Screen functions share app state; app.js owns initialization and routing.
function savedContent() {
  if (!stored.books.length && !stored.advice.length)
    return `<div class="empty">${icon("bookmark")}<h2>마음에 남은 시선을 모아두세요.</h2><p>대화 속 조언과 추천받은 책을 이 브라우저에 담아둘 수 있어요.<br>${RETENTION_NOTICE}</p></div>`;
  return `${stored.books.map((id) => bookCard(id, `저장한 책 · ${AUTHORS[BOOKS[id].author].name}`, true)).join("")}${stored.advice.map((m) => `<article class="saved-item"><div class="saved-meta"><span>${AUTHORS[m.author].name} · ${esc(m.date)}</span><button class="icon-button" data-remove-advice="${m.id}" aria-label="저장한 조언 삭제">${icon("trash")}</button></div>${m.title ? `<h3>${esc(m.title)}</h3>` : ""}<p>${esc(m.body)}</p>${m.question ? `<p class="question">${esc(m.question)}</p>` : ""}${quotationHTML(m)}${m.book && BOOKS[m.book] ? `<button class="text-button" data-book="${m.book}">『${BOOKS[m.book].title}』에서 빌린 시선 ${icon("right")}</button>` : ""}</article>`).join("")}<p class="fine">이 브라우저에 임시로 저장한 책과 조언이에요.<br>${RETENTION_NOTICE}</p>`;
}
function saveAdvice(id) {
  const m = sessions[state.author].messages.find(
    (x) => x.id === id && x.role === "assistant",
  );
  if (!m) return;
  const exists = stored.advice.some((x) => x.id === id);
  if (exists) stored.advice = stored.advice.filter((x) => x.id !== id);
  else
    stored.advice.unshift({
      ...m,
      date: new Date().toLocaleDateString("ko-KR"),
    });
  const ok = persist();
  render({ keep: true });
  if (ok)
    notify(
      exists
        ? "저장한 조언을 꺼냈어요."
        : "이 조언을 브라우저에 임시로 저장했어요.",
    );
}
function saveBook(id) {
  const exists = stored.books.includes(id);
  stored.books = exists
    ? stored.books.filter((x) => x !== id)
    : [id, ...stored.books];
  const ok = persist();
  if ($("#dialog").open) bookDetail(id);
  render({ keep: true });
  if (ok)
    notify(exists ? "기록에서 꺼냈어요." : "이 브라우저의 기록에 담았어요.");
}
function recordsPage() {
  const view = ["conversations", "letters", "prophecies"].includes(
    state.recordView,
  )
    ? state.recordView
    : "conversations";
  return `<div class="record-segments" aria-label="기록 분류">${[
    ["conversations", "대화 기록"],
    ["letters", "편지함"],
    ["prophecies", "예언"],
  ]
    .map(
      ([v, l]) =>
        `<button data-record-view="${v}" aria-pressed="${view === v}" class="${view === v ? "active" : ""}">${l}</button>`,
    )
    .join(
      "",
    )}</div>${view === "letters" ? mailbox() : view === "prophecies" ? prophecyArchivePage() : conversationRecordsPage()}`;
}
