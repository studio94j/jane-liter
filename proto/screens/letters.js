"use strict";
// Screen functions share app state; app.js owns initialization and routing.
function chars(t) {
  const normalized = String(t).normalize("NFC");
  return segmenter
    ? Array.from(segmenter.segment(normalized), (x) => x.segment)
    : Array.from(normalized);
}
function dayKey() {
  const p = new Intl.DateTimeFormat("en-CA", {
    timeZone: ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  return ["year", "month", "day"]
    .map((t) => p.find((x) => x.type === t).value)
    .join("-");
}
function dayDate(key) {
  return new Date(key + "T12:00:00+09:00");
}
function dateLabel(key) {
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: ZONE,
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
  }).format(dayDate(key));
}
function readLetters() {
  try {
    const v = JSON.parse(localStorage.getItem(letterKey) || "{}");
    return Object.fromEntries(
      Object.entries(v).filter(
        ([d, x]) =>
          /^\d{4}-\d{2}-\d{2}$/.test(d) &&
          x &&
          x.date === d &&
          typeof x.body === "string" &&
          chars(x.body).length <= 100,
      ),
    );
  } catch {
    return {};
  }
}
function today() {
  const date = dayKey(),
    d = dayDate(date),
    saved = letters[date],
    a = AUTHORS[state.author];
  return `<div class="screen day-screen"><div class="day-top"><span>하루 한 통, 백 자의 마음</span><button class="text-button" data-page="letters">편지함 ${icon("right")}</button></div><div class="calendar-art"><span class="month-side">${new Intl.DateTimeFormat("en", { month: "long", timeZone: ZONE }).format(d).toUpperCase()}</span><div class="calendar-center"><p>${date.slice(0, 4)} <span>·</span> ${date.slice(5, 7)}</p><strong>${new Intl.DateTimeFormat("en", { day: "numeric", timeZone: ZONE }).format(d)}</strong></div><span class="weekday-side">${new Intl.DateTimeFormat("en", { weekday: "short", timeZone: ZONE }).format(d).toUpperCase()}</span></div><div class="day-letter"><div class="day-letter-label"><span>부치지 않을 편지</span><span>${saved ? "오늘의 한 통 · 보관됨" : "오늘의 한 통 · 아직 빈자리"}</span></div>${saved ? `<p class="day-letter-body">${esc(saved.body)}</p><p class="day-letter-to">${esc(saved.recipient || "오늘의 나에게")} · ${chars(saved.body).length}자</p>` : `<h1>말하지 못한 마음을,<br>백 자 안에 놓아두세요.</h1><p class="sub">설렘, 서운함, 아직 남은 그리움.<br>미처 말하지 못한 마음을 남겨요.</p>`}</div><div class="stack today-actions"><button class="primary" data-action="write-letter">${icon("quill")}${saved ? "오늘의 편지 다듬기" : "오늘의 편지 쓰기"}</button></div><button class="chosen-author" data-page="settings"><img src="${a.image}" alt=""><span><small>곁에 둔 작가</small><strong>${a.name}</strong></span><span class="chosen-caption">${a.tags[0]}<br>다음에도 함께해요</span>${icon("right")}</button><p class="fine">대화 없이 편지만 남겨도 괜찮아요.</p></div>`;
}
function mailbox() {
  const entries = Object.values(letters).sort((a, b) =>
    b.date.localeCompare(a.date),
  );
  return `<div class="screen mailbox"><p class="eyebrow">LETTERS NEVER SENT</p><div class="saved-header"><h1>부치지 않은<br>마음들이 모이는 곳.</h1><span>${String(entries.length).padStart(2, "0")}</span></div><p class="sub">하루에 한 통, 그날의 마음은 백 자 안에.</p><button class="primary" style="margin-top:23px" data-action="write-letter">${letters[dayKey()] ? "오늘의 편지 다듬기" : "오늘의 편지 쓰기"} ${icon("quill")}</button>${entries.length ? entries.map((l) => `<button class="letter-row" data-letter="${l.date}"><span class="letter-day"><strong>${Number(l.date.slice(8))}</strong><small>${l.date.slice(0, 7).replace("-", ".")}</small></span><span class="letter-row-copy"><span>${esc(l.recipient || "오늘의 나에게")}</span><p>${esc(l.body)}</p><small>${chars(l.body).length}자 · ${l.author && AUTHORS[l.author] ? AUTHORS[l.author].name + "과 대화 후" : "혼자 적은 마음"}</small></span>${icon("right")}</button>`).join("") : `<div class="empty">${icon("quill")}<h2>아직 부치지 않은 마음이 있나요?</h2><p>한 문장이면 충분해요.<br>현재 브라우저에 남아 있는 편지가 날짜별로 모여요.</p></div>`}<p class="fine">${RETENTION_NOTICE}<br>편지는 이 브라우저에 임시로 저장돼요. 공유 기기에서는 다른 사람도 읽을 수 있어요.</p></div>`;
}
function openLetter(origin = "direct") {
  const key = dayKey();
  letters = readLetters();
  editor.returnPage = state.page === "write" ? "today" : state.page;
  editor.date = key;
  editor.origin = origin;
  const saved = letters[key],
    draft = letterDrafts[key];
  Object.assign(editor, {
    body: draft?.body ?? saved?.body ?? "",
    recipient: draft?.recipient ?? saved?.recipient ?? "오늘의 나에게",
    author:
      draft?.author ??
      saved?.author ??
      (origin === "chat" ? state.author : null),
    base: draft ? draft.base : (saved?.updatedAt ?? null),
    dirty: !!draft,
    view: "paper",
  });
  go("write");
}
function gridMarkup(body) {
  const items = chars(body);
  return Array.from(
    { length: 100 },
    (_, i) =>
      `<span class="manuscript-cell ${items[i] ? "filled" : ""}">${items[i] === "\n" ? "↵" : esc(items[i] || "")}</span>`,
  ).join("");
}
function writer() {
  const count = chars(editor.body).length;
  return `<div class="screen writer"><div class="writer-date"><span>${dateLabel(editor.date)}</span><span>하루 1통</span></div><div class="letter-title"><p class="eyebrow">A LETTER, JUST FOR YOU</p><h1>부치지 않을 편지</h1></div>${editor.origin === "chat" && sessions[state.author].messages.some((m) => m.role === "user") ? `<button class="bring-words" data-action="bring-words">${icon("chat")} 대화에서 내가 한 말 가져오기 ${icon("right")}</button>` : ""}<div class="letter-canvas">${editor.view === "paper" ? `<label class="sr-only" for="letter-input">편지 본문, 공백 포함 100자 이내</label><textarea id="letter-input" aria-describedby="letter-limit" placeholder="오늘은 끝내 하지 못한 말이 있었다.&#10;&#10;누구에게도 보내지 않을,&#10;나의 마음을 이곳에 남긴다." spellcheck="false">${esc(editor.body)}</textarea>` : `<button class="manuscript" data-action="edit-paper" aria-label="100칸 원고지 미리보기, 눌러서 편집">${gridMarkup(editor.body)}</button><p class="fine">원고지를 누르면 편지지에서 이어 쓸 수 있어요.</p>`}</div><div class="letter-count"><span id="letter-limit">공백·문장부호·줄바꿈 포함</span><strong id="letter-count" class="${count > 100 ? "over" : ""}">${count} <small>/ 100</small></strong></div><p id="letter-error" class="letter-error" role="status">${count > 100 ? `${count - 100}자를 줄이면 보관할 수 있어요.` : ""}</p><div class="stack writer-actions"><button class="primary" id="save-letter" data-action="save-letter" ${count > 100 || !editor.body.trim() ? "disabled" : ""}>${letters[editor.date] ? "오늘의 편지 수정해 보관하기" : "오늘의 편지 보관하기"} ${icon("bookmark")}</button><button class="text-button" data-action="return-from-letter">${editor.returnPage === "chat" ? "대화로 돌아가기" : "편지함으로 돌아가기"} ${icon("arrow")}</button></div><p class="fine">${letters[editor.date] ? "오늘 보관한 한 통을 다듬어요. 새 편지가 추가되지 않아요." : "한 문장만 적어도 괜찮아요. 오늘은 이 한 통이면 충분해요."}<br>보관을 누르기 전의 글은 현재 창에만 남아요.<br>${RETENTION_NOTICE}</p></div>`;
}
function updateDraft() {
  letterDrafts[editor.date] = {
    body: editor.body,
    recipient: editor.recipient,
    author: editor.author,
    base: editor.base,
  };
  editor.dirty = true;
}
function saveLetter() {
  const body = editor.body.normalize("NFC"),
    count = chars(body).length;
  if (!body.trim() || count > 100) {
    notify("편지는 1~100자 이내로 적어 주세요.");
    return;
  }
  if (editor.date !== dayKey()) {
    notify(
      "날짜가 바뀌었어요. 작성한 글을 복사한 뒤 오늘의 편지를 다시 열어 주세요.",
    );
    return;
  }
  const latest = readLetters();
  if ((latest[editor.date]?.updatedAt ?? null) !== editor.base) {
    dialog(
      "다른 창에서 편지가 바뀌었어요.",
      `<p class="prose">지금 작성한 글을 그대로 두려면 돌아가기를 선택하세요. 보관본을 불러오면 작성 중인 글 대신 다른 창에서 저장한 편지로 편집을 다시 시작합니다.</p><div class="stack"><button class="primary" data-action="reload-saved-letter">보관본으로 편집 다시 시작</button><button class="secondary" data-action="close">작성 중인 글로 돌아가기</button></div>`,
    );
    return;
  }
  const entry = {
    date: editor.date,
    body,
    recipient: editor.recipient,
    author: editor.author,
    updatedAt: cryptoId(),
  };
  latest[editor.date] = entry;
  try {
    localStorage.setItem(letterKey, JSON.stringify(latest));
  } catch {
    notify("편지를 저장하지 못했어요. 작성한 글은 현재 창에 유지됩니다.");
    return;
  }
  letters = latest;
  delete letterDrafts[editor.date];
  editor.dirty = false;
  editor.base = entry.updatedAt;
  go("today");
  notify("오늘의 편지를 브라우저에 임시로 보관했어요.");
}
function viewLetter(key) {
  const l = letters[key];
  if (!l) return;
  dialog(
    "부치지 않을 편지",
    `<p class="sub">${dateLabel(key)}</p><p class="detail-label">${esc(l.recipient || "오늘의 나에게")}</p><div class="saved-letter-grid manuscript" aria-label="100칸 원고지">${gridMarkup(l.body)}</div><p class="sr-only">${esc(l.body)}</p><div class="letter-count"><span>${l.author && AUTHORS[l.author] ? AUTHORS[l.author].name + "과 대화 후" : "혼자 적은 마음"}</span><strong>${chars(l.body).length}<small> / 100</small></strong></div><div class="stack">${key === dayKey() ? '<button class="primary" data-action="write-letter">오늘의 편지 다듬기</button>' : ""}<button class="text-button danger" data-delete-letter="${key}">이 편지 삭제</button></div>`,
  );
}
function bringWords() {
  const items = sessions[state.author].messages.filter(
    (m) => m.role === "user",
  );
  dialog(
    "내가 했던 말에서 시작하기",
    `<p class="sub">가져온 뒤 직접 고쳐 쓸 수 있어요. 100자를 넘으면 줄여서 보관해 주세요.</p>${items.map((m, i) => `<button class="words-choice" data-import-words="${i}"><span>${esc(m.body)}</span><small>${chars(m.body).length}자 ${icon("right")}</small></button>`).join("")}`,
  );
}
document.addEventListener("input", (e) => {
  if (e.target.id === "letter-input") {
    editor.body = e.target.value;
    updateDraft();
    const n = chars(editor.body).length;
    $("#letter-count").innerHTML = n + " <small>/ 100</small>";
    $("#letter-count").classList.toggle("over", n > 100);
    $("#letter-error").textContent =
      n > 100 ? n - 100 + "자를 줄이면 보관할 수 있어요." : "";
    $("#save-letter").disabled = n > 100 || !editor.body.trim();
  }
});
document.addEventListener("change", (e) => {
  if (e.target.id === "recipient") {
    editor.recipient = e.target.value;
    updateDraft();
  }
});
document.addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (!b || b.disabled) return;
  const d = b.dataset;
  if (d.letterView) {
    editor.view = d.letterView;
    render({ keep: true });
    return;
  }
  if (d.letter) {
    viewLetter(d.letter);
    return;
  }
  if (d.importWords !== undefined) {
    const m = sessions[state.author].messages.filter((x) => x.role === "user")[
      Number(d.importWords)
    ];
    if (m) {
      editor.body = m.body;
      editor.author = state.author;
      updateDraft();
      closeDialog();
      render();
    }
    return;
  }
  if (d.deleteLetter) {
    dialog(
      "이 편지를 삭제할까요?",
      `<p class="prose">${dateLabel(d.deleteLetter)}의 편지를 삭제합니다. 되돌릴 수 없어요.</p><div class="stack"><button class="primary" data-confirm-delete="${d.deleteLetter}">이 편지 삭제하기</button><button class="secondary" data-action="close">편지 유지하기</button></div>`,
    );
    return;
  }
  if (d.confirmDelete) {
    const next = readLetters();
    delete next[d.confirmDelete];
    try {
      localStorage.setItem(letterKey, JSON.stringify(next));
      letters = next;
      closeDialog();
      render();
      notify("편지를 삭제했어요.");
    } catch {
      notify("삭제하지 못했어요. 다시 시도해 주세요.");
    }
    return;
  }
  switch (d.action) {
    case "write-letter":
      openLetter();
      break;
    case "chat-letter":
      openLetter("chat");
      break;
    case "save-letter":
      saveLetter();
      break;
    case "bring-words":
      bringWords();
      break;
    case "return-from-letter":
      go(editor.returnPage === "chat" ? "chat" : "today");
      break;
    case "edit-paper":
      editor.view = "paper";
      render({ keep: true });
      $("#letter-input").focus();
      break;
    case "reload-saved-letter":
      letters = readLetters();
      {
        const latest = letters[editor.date];
        editor.body = latest?.body || "";
        editor.recipient = latest?.recipient || "오늘의 나에게";
        editor.author = latest?.author || null;
        editor.base = latest?.updatedAt || null;
        editor.dirty = false;
        delete letterDrafts[editor.date];
        closeDialog();
        render();
      }
      break;
    case "delete-all-letters":
      dialog(
        "편지함을 비울까요?",
        `<p class="prose">보관된 편지를 모두 삭제합니다. 되돌릴 수 없어요. 선택한 작가 설정은 유지됩니다.</p><div class="stack"><button class="primary" data-action="confirm-delete-all-letters">편지함 모두 삭제</button><button class="secondary" data-action="close">편지 유지하기</button></div>`,
      );
      break;
    case "confirm-delete-all-letters":
      try {
        localStorage.setItem(letterKey, "{}");
        letters = {};
        closeDialog();
        render();
        notify("편지함을 비웠어요.");
      } catch {
        notify("삭제하지 못했어요.");
      }
      break;
  }
});
window.addEventListener("storage", (e) => {
  if (e.key === letterKey) {
    letters = readLetters();
    if (state.page === "records") render({ keep: true });
  }
});
window.addEventListener("beforeunload", (e) => {
  if (Object.keys(letterDrafts).length) {
    e.preventDefault();
    e.returnValue = "";
  }
});
