"use strict";
// Screen functions share app state; app.js owns initialization and routing.
function messageHTML(m) {
  if (m.role === "user")
    return `<div class="user-message message"><p class="user-bubble">${esc(m.body)}</p></div>`;
  const a = AUTHORS[m.author],
    isSaved = stored.advice.some((x) => x.id === m.id);
  return `<article class="message ${m.safety ? "safety" : ""}" data-message="${m.id}"><div class="message-author"><img src="${a.image}" alt=""><span>${m.safety ? "안전 안내" : a.name}</span><small>${m.safety ? "먼저 확인해 주세요" : "작품에서 빌린 시선"}</small></div><div class="assistant-content"><div class="assistant-bubble">${m.title ? `<h2>${esc(m.title)}</h2>` : ""}<p class="message-body">${esc(m.body)}</p>${m.question ? `<p class="question">${esc(m.question)}</p>` : ""}${m.book ? bookCard(m.book) : ""}${m.incomplete ? '<p class="response-note">완료되지 않은 답변</p>' : ""}${m.limited ? '<p class="response-note">이어서 이야기를 나눠 보세요.</p>' : ""}${quotationHTML(m)}${sourceLinkHTML(m)}</div>${m.id !== "welcome" && !m.safety && !m.streaming && !m.incomplete ? `<div class="message-actions"><button data-save-advice="${m.id}" aria-pressed="${isSaved}">${icon(isSaved ? "check" : "bookmark")}${isSaved ? "기록에 저장됨" : "조언 저장"}</button>${m.book ? `<button data-book="${m.book}">${icon("info")}작품 맥락</button>` : ""}</div>` : ""}</div></article>`;
}
function openingHTML(author) {
  const a = AUTHORS[author],
    q = a.opening;
  return `<article class="message opening-message" data-message="welcome"><div class="message-author"><img src="${a.image}" alt=""><span>${esc(a.name)}</span><small>작품 속 한 문장</small></div><figure class="opening-quote"><blockquote lang="ko">${esc(q.korean)}</blockquote><p class="opening-english" lang="en">${esc(q.english)}</p><figcaption>『${esc(q.title)}』 · ${esc(q.speaker)}의 대사${q.edition ? "<br>" + esc(q.edition) : ""}</figcaption></figure></article>`;
}
function chat() {
  const a = AUTHORS[state.author],
    s = sessions[state.author],
    started = s.messages.length > 0;
  return `<div class="chat-layout"><section class="thread" id="thread" role="log" aria-label="${a.name}과의 대화" aria-live="polite" aria-relevant="additions"><p class="chat-date">A conversation with ${a.en}</p><p class="trial-notice">${RETENTION_NOTICE}</p>${openingHTML(a.id)}${chatMessagesHTML(s)}${!s.pending ? situationSuggestions() : ""}${s.pending ? typing(a.id, s.loadingStage) : ""}${localErrorHTML(s)}</section><div class="composer-area">${started && !s.pending && !s.error && !s.messages.at(-1)?.safety ? `<div class="suggestions" aria-label="대화 이어가기"><button data-follow="concrete">좀 더 현실적으로 말해 줘요</button><button data-follow="book">이 관점을 더 설명해 줘요</button><button data-follow="message">어떻게 말하면 좋을까요?</button></div>` : ""}<form class="composer" id="chat-form"><label class="sr-only" for="chat-input">${a.name}에게 보낼 이야기</label><textarea id="chat-input" rows="1" maxlength="2000" placeholder="${a.name}에게 고민을 들려주세요…" ${s.pending ? "disabled" : ""}>${esc(s.draft)}</textarea><button class="send" type="submit" aria-label="메시지 보내기" ${s.pending || !s.draft.trim() ? "disabled" : ""}>${icon("up")}</button></form>${s.pending ? `<div class="generation-controls"><span data-loading-status>${esc(loadingStatus(a.id, s.loadingStage))}</span><button data-action="stop-local">생성 중단</button></div>` : ""}<div class="composer-foot"><span id="input-count" class="chat-counter">${s.draft.length}/2000</span><span class="daily-quota" data-daily-quota aria-live="polite" title="이 브라우저의 오늘 대화 사용 횟수 · 한국 시간 자정 초기화">${dailyQuotaText()}</span></div></div></div>`;
}
function typing(author, stage) {
  if (stage === "writing") return "";
  return `<div class="typing literary-loading"><div class="loading-heading"><span class="typing-dots" aria-hidden="true"><i></i><i></i><i></i></span><span class="loading-status" role="status" aria-live="polite">${esc(loadingStatus(author, stage))}</span></div></div>`;
}
function scrollChat() {
  const el = $("#thread");
  if (el) el.scrollTop = el.scrollHeight;
}
function chatMenu() {
  dialog(
    "이 대화에서",
    `<div class="stack"><button class="secondary" data-action="memory-settings">대화 기억 안내</button><button class="secondary" data-page="settings">작가 설정</button><button class="secondary" data-profile="${state.author}">${AUTHORS[state.author].name}의 관점 살펴보기</button><button class="secondary" data-action="open-own-books">${AUTHORS[state.author].name}의 작품 보기</button><button class="secondary" data-action="new-chat">이 조언가와 새 대화 시작</button><button class="text-button" data-action="about">프로토타입과 저장 안내 ${icon("info")}</button></div>`,
  );
}
