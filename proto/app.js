"use strict";
const $ = (s) => document.querySelector(s);
const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const icon = (n) =>
  n === "check"
    ? '<span class="status-check" aria-hidden="true">✓</span>'
    : `<svg class="jane-icon" data-icon="${n}" viewBox="0 0 32 32" aria-hidden="true">${JANE_ICONS[n] || JANE_ICONS.book}</svg>`;
let storageOK = true,
  stored = { books: [], advice: [], read: [] };
try {
  const v = JSON.parse(localStorage.getItem("jane-proto-v2") || "{}");
  stored.books = Array.isArray(v.books)
    ? v.books.filter((id) => BOOKS[id])
    : [];
  stored.read = Array.isArray(v.read) ? v.read.filter((id) => BOOKS[id]) : [];
  stored.advice = Array.isArray(v.advice)
    ? v.advice.filter(
        (x) =>
          x &&
          AUTHORS[x.author] &&
          typeof x.body === "string" &&
          typeof x.id === "string",
      )
    : [];
} catch {
  storageOK = false;
}
const sessions = Object.fromEntries(
  Object.keys(AUTHORS).map((id) => [
    id,
    {
      ...ChatArchive.load(id),
      topic: "general",
      pending: false,
      draft: "",
      lastBook: null,
    },
  ]),
);
const state = {
  page: "chat",
  author: "austen",
  libraryAuthor: "austen",
  shelfTab: "books",
  savedFilter: "all",
  readingBook: null,
};
const RETENTION_NOTICE =
  "정식 출시 전 체험 버전으로, 대화와 기록이 계속 보관되지 않을 수 있어요. 간직하고 싶은 내용은 따로 복사해 주세요.";
let toastTimer;
function notify(t) {
  $("#toast").textContent = t;
  $("#toast").classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => $("#toast").classList.remove("visible"), 2200);
}
function persist() {
  try {
    localStorage.setItem("jane-proto-v2", JSON.stringify(stored));
    storageOK = true;
    return true;
  } catch {
    storageOK = false;
    notify("현재 창에만 보관돼요. 브라우저 저장을 사용할 수 없어요.");
    return false;
  }
}
function cover(id) {
  const b = BOOKS[id];
  return `<span class="mini-cover" style="--cover:${b.color}" aria-hidden="true"><small>JANE CLASSICS</small><span>${b.en.replace("\n", "<br>")}</span><small>${AUTHORS[b.author].en.toUpperCase()}</small></span>`;
}
function bookCard(id, label, full = false) {
  const b = BOOKS[id];
  return `<button class="${full ? "book-row" : "recommendation"}" data-book="${id}">${cover(id)}<span class="rec-copy"><small>${label || `${AUTHORS[b.author].name}의 작품에서`}</small><strong>${b.title}</strong><p>${b.short}</p>${full ? `<p class="book-time">${b.time} · ${b.year}</p>` : ""}</span>${icon("right")}</button>`;
}
function nav() {
  const active =
    state.page === "settings"
      ? state.primaryPage || "chat"
      : state.page === "write"
        ? "records"
        : state.page;
  return [
    ["chat", "chat", "대화"],
    ["records", "quill", "나의 기록"],
  ]
    .map(
      ([p, i, l]) =>
        `<button class="nav-button ${active === p ? "active" : ""}" data-page="${p}" ${active === p ? 'aria-current="page"' : ""}>${icon(i)}<span>${l}</span></button>`,
    )
    .join("");
}

function render(opts = {}) {
  const oldScroll = $("#main").scrollTop,
    threadScroll = $("#thread")?.scrollTop || 0;
  $("#header").innerHTML = header();
  $("#main").className = state.page === "chat" ? "chat-main" : "";
  $("#main").innerHTML = (
    { records: recordsPage, settings: settingsPage, chat, write: writer }[
      state.page
    ] || today
  )();
  $("#nav").innerHTML = nav();
  syncProphecySnackbar();
  syncLetterSnackbar();
  if (opts.keep) {
    $("#main").scrollTop = oldScroll;
    if ($("#thread")) $("#thread").scrollTop = threadScroll;
  } else {
    $("#main").scrollTop = 0;
  }
  if (opts.bottom && $("#thread")) scrollChat();
}
function go(page) {
  if (page === "settings" && state.page !== "settings")
    state.settingsReturn = state.page;
  closeDialog();
  if (["records", "today", "letters", "saved"].includes(page)) {
    state.recordView =
      page === "records"
        ? state.recordView || "conversations"
        : page === "today"
          ? "letters"
          : page === "saved"
            ? "conversations"
            : page;
    state.page = "records";
  } else
    state.page = ["advisors", "settings"].includes(page)
      ? "settings"
      : page === "shelf"
        ? "records"
        : page;
  if (
    state.page === "chat" ||
    state.page === "records" ||
    state.page === "write"
  )
    state.primaryPage = state.page === "write" ? "records" : state.page;
  history.replaceState(null, "", "#" + state.page);
  render({
    bottom: state.page === "chat" && sessions[state.author].messages.length > 0,
  });
}
function closeDialog() {
  if ($("#dialog").open) $("#dialog").close();
}
function dialog(title, body, variant = "") {
  closeDialog();
  $("#dialog").classList.toggle(
    "author-profile-dialog",
    variant === "author-profile",
  );
  $("#dialog-content").innerHTML =
    `<h2 class="dialog-title" id="dialog-title">${title}</h2>${body}`;
  $("#dialog").showModal();
}
function bookDetail(id) {
  const b = BOOKS[id],
    a = AUTHORS[b.author];
  dialog(
    "대화와 이어지는 작품",
    `<div class="dialog-book-head">${cover(id)}<div><p class="eyebrow">${a.en}</p><h3>${b.title}</h3><p>${a.full}<br>${b.tag}</p></div></div><p class="prose">${b.short}</p>${b.warning ? `<div class="notice">${b.warning}</div>` : ""}<p class="detail-label">이 조언이 시작된 장면</p><p class="prose">${b.scene}</p><p class="detail-label">작품에서 빌린 관점</p><p class="prose">${b.lens}</p><p class="detail-label">먼저 읽을 부분</p><p class="prose">${b.part}</p><p class="sub">${b.time} · 원문은 외부 영문 판본으로 연결돼요.</p><div class="stack"><button class="primary" data-read="${id}">한 장면 읽기 ${icon("book")}</button><button class="secondary" data-save-book="${id}" aria-pressed="${stored.books.includes(id)}">${icon(stored.books.includes(id) ? "check" : "bookmark")}${stored.books.includes(id) ? "기록에 담았어요 · 저장 취소" : "기록에 담기"}</button></div><div class="source">${b.sourceName}<br><a href="${b.source}" target="_blank" rel="noopener noreferrer">작품 원문과 맥락 확인 ${icon("external")}</a><p>위 내용은 Jane의 장면 요약과 해석이며 원문 인용이나 출간 번역문이 아닙니다.</p></div>`,
  );
}
function readScene(id) {
  const b = BOOKS[id];
  state.readingBook = id;
  dialog(
    b.title,
    `<p class="eyebrow">A SCENE TO SIT WITH</p><p class="sub">${b.part}<br>Jane의 장면 요약 · 원문 인용 아님</p>${b.warning ? `<p class="notice">${b.warning}</p>` : ""}<div class="scene-reader reader-rule"><p>${b.scene}</p><p>${b.lens}</p></div><p class="detail-label">나에게 돌려보는 질문</p><p class="scene-reader">${b.question}</p><div class="stack"><button class="primary" data-read-done="${id}" aria-pressed="${stored.read.includes(id)}">${stored.read.includes(id) ? "✓ 이 장면을 읽었어요" : "이 장면 읽음 표시"}</button><button class="secondary" data-action="back-chat">${AUTHORS[state.author].name}과 대화 이어가기 ${icon("arrow")}</button></div><div class="source"><a href="${b.source}" target="_blank" rel="noopener noreferrer">${b.sourceName}에서 이어 읽기 ${icon("external")}</a></div>`,
  );
}
function cryptoId() {
  return (
    globalThis.crypto?.randomUUID?.() ||
    `${Date.now()}-${Math.random().toString(36).slice(2)}`
  );
}
const ZONE = "Asia/Seoul";
const letterKey = "jane-letters-v3",
  prefKey = "jane-preferences";
const segmenter =
  typeof Intl.Segmenter === "function"
    ? new Intl.Segmenter("ko", { granularity: "grapheme" })
    : null;
let letters = readLetters();
const editor = {
  date: null,
  body: "",
  recipient: "오늘의 나에게",
  view: "paper",
  origin: "direct",
  author: null,
  base: null,
  returnPage: "today",
  dirty: false,
};
const letterDrafts = {};
try {
  const p = JSON.parse(localStorage.getItem(prefKey) || "{}");
  if (AUTHORS[p.author]) state.author = p.author;
} catch {}
state.libraryAuthor = state.author;

function header() {
  $("#header").className =
    state.page === "chat" ? "header header-chat" : "header";
  if (state.page === "settings")
    return `<button class="icon-button" data-action="settings-back" aria-label="이전 화면으로">${icon("back")}</button><span class="topbar-title">설정</span>`;
  const settings = `<button class="icon-button topbar-settings" data-page="settings" aria-label="설정">${icon("settings")}</button>`;
  if (state.page === "chat") {
    const a = AUTHORS[state.author];
    return `<img class="chat-avatar" src="${a.image}" alt=""><div class="chat-head-copy"><h1>${a.name}</h1><p>${{ austen: "따스하고 예리한", william: "극적이고 통찰력 있는", chekhov: "담담하고 시니컬한" }[a.id]}</p></div><button class="icon-button" data-action="chat-menu" aria-label="대화 메뉴">${icon("more")}</button>${settings}`;
  }
  return `<button class="wordmark" data-page="chat" aria-label="Jane 대화 홈">jane<span>.</span></button><span class="header-label">${state.page === "write" ? "부치지 않을 편지" : "나의 기록"}</span>${settings}`;
}

$("#dialog").addEventListener("click", (e) => {
  if (e.target === $("#dialog")) {
    const r = e.target.getBoundingClientRect();
    if (e.clientY < r.top || e.clientX < r.left || e.clientX > r.right)
      closeDialog();
  }
});
document.addEventListener("input", (e) => {
  if (e.target.id !== "chat-input") return;
  const t = e.target;
  sessions[state.author].draft = t.value;
  $(".send").disabled = !t.value.trim();
  $("#input-count").textContent = t.value.length + "/2000";
  t.style.height = "34px";
  t.style.height = Math.min(t.scrollHeight, 100) + "px";
});
document.addEventListener("keydown", (e) => {
  if (
    e.target.id === "chat-input" &&
    e.key === "Enter" &&
    !e.shiftKey &&
    !e.isComposing &&
    e.keyCode !== 229
  ) {
    e.preventDefault();
    send(e.target.value);
  }
});
document.addEventListener("submit", (e) => {
  if (e.target.id === "chat-form") {
    e.preventDefault();
    send($("#chat-input").value);
  }
});
document.addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (!b || b.disabled) return;
  const d = b.dataset;
  if (d.page) {
    go(d.page);
    return;
  }
  if (d.author) {
    chooseAuthor(d.author);
    render({ keep: true });
    return;
  }
  if (d.chatAuthor) {
    chooseAuthor(d.chatAuthor);
    go("chat");
    return;
  }
  if (d.profile) {
    profile(d.profile);
    return;
  }
  if (d.book) {
    bookDetail(d.book);
    return;
  }
  if (d.read) {
    readScene(d.read);
    return;
  }
  if (d.saveBook) {
    saveBook(d.saveBook);
    return;
  }
  if (d.saveAdvice) {
    saveAdvice(d.saveAdvice);
    return;
  }
  if (d.removeAdvice) {
    stored.advice = stored.advice.filter((x) => x.id !== d.removeAdvice);
    const ok = persist();
    render({ keep: true });
    if (ok) notify("저장한 조언을 삭제했어요.");
    return;
  }
  if (d.prompt) {
    const text = starterText(state.author, d.prompt);
    if (text) send(text);
    return;
  }
  if (d.follow) {
    send(
      {
        concrete: "좀 더 현실적으로 말해 줘요.",
        book: "이 관점을 더 설명해 줘요",
        message: "어떻게 말하면 좋을까요?",
      }[d.follow],
      d.follow,
    );
    return;
  }
  if (d.shelfTab) {
    state.shelfTab = d.shelfTab;
    render();
    return;
  }
  if (d.libraryAuthor) {
    state.libraryAuthor = d.libraryAuthor;
    render({ keep: true });
    return;
  }
  if (d.readDone) {
    if (!stored.read.includes(d.readDone)) stored.read.push(d.readDone);
    const ok = persist();
    b.innerHTML = "✓ 이 장면을 읽었어요";
    b.setAttribute("aria-pressed", "true");
    if (ok) notify("읽은 장면을 기록했어요.");
    return;
  }
  switch (d.action) {
    case "settings-back":
      go(state.settingsReturn || state.primaryPage || "chat");
      break;
    case "close":
      closeDialog();
      break;
    case "about":
      about();
      break;
    case "start":
      go("chat");
      break;
    case "switch":
      switchDialog();
      break;
    case "try-example":
      go("chat");
      send(TOPICS.conflict.sample);
      break;
    case "chat-menu":
      chatMenu();
      break;
    case "back-chat":
      go("chat");
      break;
    case "open-own-books":
      openAuthorBooks();
      break;
    case "new-chat":
      dialog(
        "새 대화를 시작할까요?",
        `<p class="prose">${AUTHORS[state.author].name}과 보관된 대화를 모두 삭제하고 새로 시작해요. 저장한 편지, 조언과 책은 유지됩니다.</p><div class="stack"><button class="primary" data-action="new-chat-confirm">새 대화 시작</button><button class="secondary" data-action="close">대화 유지하기</button></div>`,
      );
      break;
    case "new-chat-confirm":
      if (sessions[state.author].pending) {
        notify("답변이 도착한 뒤 새 대화를 시작해 주세요.");
        break;
      }
      if (!ChatArchive.clear(state.author)) break;
      sessions[state.author] = {
        ...ChatArchive.load(state.author),
        topic: "general",
        pending: false,
        draft: "",
        lastBook: null,
      };
      go("chat");
      break;
    case "reset-confirm":
      dialog(
        "저장 기록을 삭제할까요?",
        `<p class="prose">v2에서 저장한 책, 조언, 읽음 표시를 모두 삭제합니다. 삭제한 기록은 되돌릴 수 없어요. v1 기록과 현재 대화는 그대로 유지됩니다.</p><div class="stack"><button class="primary" data-action="reset">저장 기록 모두 삭제</button><button class="secondary" data-action="close">기록 유지하기</button></div>`,
      );
      break;
    case "reset":
      stored = { books: [], advice: [], read: [] };
      const ok = persist();
      closeDialog();
      render({ keep: true });
      if (ok) notify("v2 저장 기록을 삭제했어요.");
      break;
  }
});
window.addEventListener("hashchange", () => {
  const p = location.hash.slice(1);
  if (
    [
      "records",
      "today",
      "advisors",
      "settings",
      "chat",
      "shelf",
      "letters",
      "saved",
    ].includes(p)
  )
    go(p);
});

document.addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (!b || b.disabled) return;
  if (b.dataset.recordView) {
    state.recordView = b.dataset.recordView;
    go("records");
  }
  if (b.dataset.settingsAuthor) {
    chooseAuthor(b.dataset.settingsAuthor);
    go("chat");
  }
});

let prophecySnackDay = "",
  prophecyConversationDay = "",
  prophecySnackTimer;
function markProphecyConversationStarted() {
  prophecyConversationDay = dayKey();
}
function dismissProphecySnackbar() {
  clearTimeout(prophecySnackTimer);
  document.querySelector("#prophecy-snackbar")?.remove();
}
function syncProphecySnackbar() {
  if (state.page !== "chat" || sessions[state.author].pending) {
    dismissProphecySnackbar();
    return;
  }
  if (prophecyConversationDay !== dayKey()) return;
  const key = "jane-prophecy-conversation-snackbar:" + dayKey();
  if (prophecySnackDay === key) return;
  prophecySnackDay = key;
  try {
    if (localStorage.getItem(key)) return;
    localStorage.setItem(key, "seen");
  } catch {}
  const bar = document.createElement("aside");
  bar.id = "prophecy-snackbar";
  bar.className = "prophecy-snackbar";
  bar.setAttribute("aria-label", "오늘의 예언");
  bar.setAttribute("role", "status");
  bar.innerHTML = `<span class="snackbar-label">${icon("sparkle")}<span>고민으로 불안한 당신,<br>예언을 받아보시겠어요?</span></span><button class="snackbar-action" data-action="open-fortune">예언 받기</button><button class="icon-button snackbar-close" aria-label="예언 알림 닫기">${icon("close")}</button>`;
  document.querySelector("#app").append(bar);
  const start = () => {
    clearTimeout(prophecySnackTimer);
    prophecySnackTimer = setTimeout(() => {
      if (bar.matches(":hover") || bar.contains(document.activeElement)) return;
      dismissProphecySnackbar();
    }, 10000);
  };
  bar.addEventListener("mouseenter", () => clearTimeout(prophecySnackTimer));
  bar.addEventListener("mouseleave", start);
  bar.addEventListener("focusin", () => clearTimeout(prophecySnackTimer));
  bar.addEventListener("focusout", start);
  bar
    .querySelector(".snackbar-close")
    .addEventListener("click", dismissProphecySnackbar);
  bar
    .querySelector(".snackbar-action")
    .addEventListener("click", () => setTimeout(dismissProphecySnackbar, 0));
  start();
}

// Offer a letter after three complete exchanges today, once per day.
let letterSnackTimer;
const letterSnackSeen = new Set();
function letterSuggestionEligible(session, today, hasLetter) {
  if (
    hasLetter ||
    session.pending ||
    session.error ||
    session.letterSuggestionDay !== today
  )
    return false;
  const last = session.messages.at(-1);
  if (
    !last ||
    last.role !== "assistant" ||
    last.streaming ||
    last.incomplete ||
    last.safety ||
    last.retrieval?.status === "safety-priority"
  )
    return false;
  return (
    session.messages.filter(
      (m) =>
        m.role === "assistant" &&
        m.day === today &&
        !m.streaming &&
        !m.incomplete &&
        !m.safety &&
        m.retrieval?.status !== "safety-priority",
    ).length >= 3
  );
}
function dismissLetterSnackbar() {
  clearTimeout(letterSnackTimer);
  document.querySelector("#letter-snackbar")?.remove();
}
function syncLetterSnackbar() {
  dismissLetterSnackbar();
  const today = dayKey(),
    key = "jane-letter-suggestion:" + today;
  if (
    state.page !== "chat" ||
    document.querySelector("#prophecy-snackbar") ||
    !letterSuggestionEligible(
      sessions[state.author],
      today,
      !!readLetters()[today],
    ) ||
    letterSnackSeen.has(key)
  )
    return;
  try {
    if (localStorage.getItem(key)) return;
    localStorage.setItem(key, "seen");
  } catch {}
  letterSnackSeen.add(key);
  const bar = document.createElement("aside");
  bar.id = "letter-snackbar";
  bar.className = "letter-snackbar";
  bar.setAttribute("role", "status");
  bar.setAttribute("aria-label", "편지 쓰기 제안");
  bar.innerHTML = `<span class="snackbar-label">${icon("quill")}<span>나눈 이야기 속 마음을<br>부치지 않을 편지로 남겨볼까요?</span></span><button class="snackbar-action" data-action="chat-letter">편지 쓰기</button><button class="icon-button snackbar-close" aria-label="편지 제안 닫기">${icon("close")}</button>`;
  document.querySelector(".composer-area").before(bar);
  const start = () => {
    clearTimeout(letterSnackTimer);
    letterSnackTimer = setTimeout(() => {
      if (bar.matches(":hover") || bar.contains(document.activeElement)) return;
      dismissLetterSnackbar();
    }, 12000);
  };
  bar.addEventListener("mouseenter", () => clearTimeout(letterSnackTimer));
  bar.addEventListener("mouseleave", start);
  bar.addEventListener("focusin", () => clearTimeout(letterSnackTimer));
  bar.addEventListener("focusout", start);
  bar
    .querySelector(".snackbar-close")
    .addEventListener("click", dismissLetterSnackbar);
  start();
}

const initial = location.hash.slice(1);
state.recordView = "conversations";
go(
  [
    "records",
    "today",
    "settings",
    "advisors",
    "chat",
    "letters",
    "saved",
    "shelf",
  ].includes(initial)
    ? initial
    : "chat",
);

let visibleDay = dayKey();
function refreshDay() {
  if (visibleDay !== dayKey()) {
    visibleDay = dayKey();
    letters = readLetters();
    if (state.page === "records") render();
    else if (state.page === "chat") render({ keep: true });
  }
}
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) refreshDay();
});
setInterval(refreshDay, 30000);

// Shared close control uses the same extracted icon set.
document.querySelector("#dialog > .close").innerHTML = icon("close");
