"use strict";
const $ = (id) => document.getElementById(id),
  frame = $("material");
let token = location.hash.slice(1) || sessionStorage.getItem("stories-token");
if (location.hash) {
  sessionStorage.setItem("stories-token", token);
  history.replaceState(null, "", location.pathname);
}
let story,
  revision,
  channel,
  bridge,
  selection = { kind: "story" },
  active = null,
  candidate = null,
  visible = true,
  agentIndex = -1,
  slideElements = null,
  slide = 0;
let draftId,
  sequence = Date.now(),
  saveTimer,
  polling = false,
  submission = null;
const viewKey = "stories-view",
  draftKey = "stories-draft";
const editor = sessionStorage.getItem("stories-editor") || crypto.randomUUID();
sessionStorage.setItem("stories-editor", editor);
const sameAnchor = (a, b) =>
  a.kind === b.kind &&
  a.element === b.element &&
  (a.kind !== "text" || (a.start === b.start && a.end === b.end));
const requestId = () => crypto.randomUUID();
function error(e) {
  $("error").textContent = e.message || String(e);
  $("error").hidden = false;
}
async function api(name, data = {}) {
  const r = await fetch("/api/" + name, {
    method: "POST",
    headers: {
      Authorization: "Bearer " + token,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  const v = await r.json();
  if (!r.ok) throw Error(v.error?.message || v.error || "Request failed");
  return v;
}
function send(type, data = {}) {
  frame.contentWindow.postMessage({ channel, type, ...data }, "*");
}
const notes = () => story.annotations.filter((n) => n.revision_id === revision);
function view() {
  localStorage.setItem(viewKey + story.id, JSON.stringify({ revision, slide }));
}
function draftIdentity() {
  const { kind, element, start, end } = selection;
  return (
    "review-" +
    editor +
    "-" +
    revision +
    "-" +
    JSON.stringify([kind, element, start, end])
  );
}
function closeComment() {
  clearTimeout(saveTimer);
  $("composer").hidden = true;
  $("quick").hidden = true;
  return saveDraft();
}
async function saveDraft() {
  if (!draftId) return;
  const id = draftId,
    text = $("comment").value,
    anchor = structuredClone(selection),
    rev = revision,
    seq = ++sequence;
  localStorage.setItem(
    draftKey + story.id,
    JSON.stringify({
      id,
      revision: rev,
      anchor,
      text,
      sequence: seq,
      active,
      open: !$("composer").hidden,
    }),
  );
  $("saved").textContent = "Saving…";
  try {
    const result = await api("save-draft", {
      revision_id: rev,
      draft_id: id,
      sequence: seq,
      text,
      anchor,
    });
    if (draftId === id && sequence === seq)
      $("saved").textContent =
        result.status === "saved" ? "Draft saved" : "Newer draft retained";
  } catch (e) {
    $("saved").textContent = "Not saved to Stories";
    error(e);
  }
}
async function openComment(anchor, note = null) {
  if (!$("composer").hidden) await saveDraft();
  selection = anchor;
  $("composer").dataset.anchor = JSON.stringify(anchor);
  active = note?.id || null;
  draftId = draftIdentity();
  $("composer").hidden = false;
  $("quick").hidden = true;
  $("author").textContent =
    note?.author === "agent" ? "From your agent" : "Your comment";
  const entry = story.drafts[draftId];
  let cached;
  try {
    cached = JSON.parse(localStorage.getItem(draftKey + story.id));
  } catch {}
  $("comment").value =
    (cached?.revision === revision && sameAnchor(cached.anchor, anchor)
      ? cached.text
      : entry?.text) || "";
  $("target").textContent =
    anchor.quote ||
    note?.anchor.quote ||
    (anchor.kind === "story" ? "Whole story" : "Selected element");
  $("outcome").textContent = "";
  renderMessages();
  $("comment").focus();
  await saveDraft();
}
function renderMessages() {
  const group = notes().filter((n) => sameAnchor(n.anchor, selection));
  const n = group.at(-1);
  const messages = group.flatMap((n) => [
    { author: n.author, text: n.text },
    ...n.responses,
  ]);
  const key = JSON.stringify(messages);
  if ($("messages").dataset.messages !== key) {
    $("messages").dataset.messages = key;
    $("messages").replaceChildren();
    for (const m of messages) {
      const row = document.createElement("div");
      row.className = "message";
      const a = document.createElement("strong");
      a.textContent =
        m.author === "agent"
          ? "Agent"
          : m.author === "stories"
            ? "Stories"
            : "You";
      row.append(a, document.createTextNode(m.text));
      $("messages").append(row);
    }
  }
  if (n)
    $("outcome").textContent =
      n.status.replaceAll("_", " ") +
      (n.result_revision ? " · revision available" : "") +
      (n.error ? " · " + n.error.message + " " + n.error.remedy : "");
}
function update() {
  const agents = notes().filter((n) => n.author === "agent");
  $("agent").hidden = !agents.length;
  $("agent").textContent = `Agent highlights · ${agents.length}`;
  $("available").hidden =
    !story.latest_revision || story.latest_revision === revision;
  send("annotations", { annotations: notes() });
  renderMessages();
  $("threads").replaceChildren();
  for (const n of notes()) {
    const b = document.createElement("button");
    b.textContent = (n.author === "agent" ? "Agent: " : "You: ") + n.text;
    b.onclick = () => {
      send("reveal", { anchor: n.anchor });
      openComment(n.anchor, n).catch(error);
    };
    $("threads").append(b);
  }
  const current = story.revisions.find((r) => r.id === revision);
  $("sources").textContent =
    (current
      ? Object.entries(current.review)
          .map(([k, v]) => k + ": " + v)
          .join("\n")
      : "No revision") +
    (current?.quality_review
      ? "\n\nModel review of " +
        current.quality_review.pages.length +
        " rendered pages\n" +
        [
          ...current.quality_review.warnings,
          ...current.quality_review.limits,
        ].join("\n")
      : "") +
    "\n\n" +
    story.sources.map((s) => s.name + "\n" + s.content).join("\n\n");
  const versions = $("versions");
  if (versions.options.length !== story.revisions.length) {
    versions.replaceChildren();
    for (const [i, r] of story.revisions.entries()) {
      const option = document.createElement("option");
      option.value = r.id;
      option.textContent = `Version ${i + 1}${r.id === story.latest_revision ? " · newest" : ""}`;
      versions.append(option);
    }
  }
  versions.value = revision;
}
async function loadRevision(id, initialSlide = 0) {
  if (!$("composer").hidden) await saveDraft();
  const p = await api("get-preview", { revision_id: id });
  revision = id;
  slide = initialSlide;
  channel = requestId();
  $("composer").hidden = true;
  $("quick").hidden = true;
  active = null;
  draftId = null;
  selection = { kind: "story" };
  const nonce = requestId();
  const csp = `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; script-src 'nonce-${nonce}'; connect-src 'none'; form-action 'none'; base-uri 'none'">`;
  let html = p.html.replace(/<head[^>]*>/i, (m) => m + csp);
  if (!/<head/i.test(html))
    html = html.replace(/<html[^>]*>/i, (m) => m + "<head>" + csp + "</head>");
  const code = bridge
    .replace("__CHANNEL__", JSON.stringify(channel))
    .replace("__SLIDE__", String(slide));
  html = html.replace(
    /<\/body>/i,
    `<script nonce="${nonce}">${code}</script></body>`,
  );
  frame.srcdoc = html;
  view();
  update();
}
async function choose(id) {
  await api("select-revision", { revision_id: id, request_id: requestId() });
  await loadRevision(id, slide);
}
window.addEventListener("message", (e) => {
  if (e.source !== frame.contentWindow || e.data?.channel !== channel) return;
  const m = e.data;
  if (m.type === "selection" && visible) {
    candidate = m.anchor;
    const existing = notes().find((n) => sameAnchor(n.anchor, candidate));
    const r = m.rect;
    $("quick").style.left =
      Math.max(10, Math.min(innerWidth - 200, r.x + r.width / 2)) + "px";
    $("quick").style.top =
      Math.max(85, Math.min(innerHeight - 80, r.y + r.height + 8)) + "px";
    $("quick").hidden = false;
    $("quick").textContent = existing ? "Open comment" : "Comment on selection";
  }
  if (m.type === "open-thread") {
    const n = notes().find((n) => n.id === m.id);
    if (n) openComment(n.anchor, n).catch(error);
  }
  if (m.type === "position") {
    slideElements = m.elements;
    if (m.slide !== slide) {
      $("quick").hidden = true;
      candidate = null;
      if (
        !$("composer").hidden &&
        selection.kind !== "story" &&
        !m.elements?.includes(selection.element)
      )
        closeComment().catch(error);
    }
    slide = m.slide;
    $("position").textContent = `${m.slide + 1} / ${m.total}`;
    view();
  }
  if (m.type === "ready") {
    send("overlay", { visible, annotations: notes() });
    let cached;
    try {
      cached = JSON.parse(localStorage.getItem(draftKey + story.id));
    } catch {}
    if (
      cached?.revision === revision &&
      cached.open &&
      (cached.anchor.kind === "story" ||
        !slideElements ||
        slideElements.includes(cached.anchor.element))
    ) {
      selection = cached.anchor;
      openComment(
        selection,
        notes().find((n) => n.id === cached.active),
      ).catch(error);
    }
  }
});
$("quick").onpointerdown = (e) => e.preventDefault();
$("quick").onclick = () =>
  openComment(
    candidate,
    notes().find((n) => sameAnchor(n.anchor, candidate)),
  ).catch(error);
$("overall").onclick = () => openComment({ kind: "story" }).catch(error);
$("close").onclick = () => closeComment().catch(error);
$("comment").oninput = () => {
  submission = null;
  clearTimeout(saveTimer);
  $("saved").textContent = "Unsaved";
  saveTimer = setTimeout(saveDraft, 250);
};
$("send").onclick = async () => {
  const text = $("comment").value;
  if (!text.trim()) return;
  $("send").disabled = true;
  clearTimeout(saveTimer);
  submission = submission || requestId();
  try {
    await saveDraft();
    const result = await api("add-comment", {
      revision_id: revision,
      text,
      anchor: selection,
      request_id: submission,
    });
    active = result.annotation_id;
    submission = null;
    $("comment").value = "";
    await saveDraft();
    story = await api("get-story");
    update();
    $("outcome").textContent =
      result.status === "awaiting_authority"
        ? "Saved · waiting for model authority"
        : result.status.replaceAll("_", " ");
  } catch (e) {
    error(e);
  } finally {
    $("send").disabled = false;
  }
};
$("agent").onclick = () => {
  const a = notes().filter((n) => n.author === "agent");
  if (!a.length) return;
  const n = a[++agentIndex % a.length];
  send("reveal", { anchor: n.anchor });
  openComment(n.anchor, n).catch(error);
};
$("overlay").onclick = async () => {
  visible = !visible;
  document.body.classList.toggle("review-hidden", !visible);
  $("overlay").textContent = visible ? "Hide review" : "Show review";
  if (!visible) {
    await saveDraft();
    $("composer").hidden = true;
    $("quick").hidden = true;
  }
  send("overlay", { visible, annotations: notes() });
};
$("previous").onclick = () => send("navigate", { delta: -1 });
$("next").onclick = () => send("navigate", { delta: 1 });
$("more").onclick = () => {
  $("details").hidden = !$("details").hidden;
};
$("closeDetails").onclick = () => {
  $("details").hidden = true;
};
$("available").onclick = () => choose(story.latest_revision).catch(error);
$("versions").onchange = (e) => choose(e.target.value).catch(error);
$("export").onclick = async () => {
  try {
    const r = await fetch("/api/download", {
      method: "POST",
      headers: {
        Authorization: "Bearer " + token,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ revision_id: revision }),
    });
    if (!r.ok) throw Error("Export failed");
    const url = URL.createObjectURL(await r.blob());
    const a = document.createElement("a");
    a.href = url;
    a.download = story.title.replace(/[^a-z0-9 -]/gi, "") + ".html";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (e) {
    error(e);
  }
};
async function boot() {
  if (!token)
    throw Error("Open the private viewer URL returned by start-dashboard.");
  bridge = await (await fetch("/bridge.js")).text();
  const initial = await api("bootstrap");
  story = initial.story;
  $("title").textContent = story.title;
  let saved;
  try {
    saved = JSON.parse(localStorage.getItem(viewKey + story.id));
  } catch {}
  const id = story.revisions.some((r) => r.id === saved?.revision)
    ? saved.revision
    : initial.revision_id || story.selected_revision;
  if (id) await loadRevision(id, saved?.revision === id ? saved.slide : 0);
  else $("connection").textContent = "Waiting for first artifact";
  setInterval(async () => {
    if (polling) return;
    polling = true;
    try {
      story = await api("get-story");
      if (!revision && story.latest_revision)
        await loadRevision(story.latest_revision);
      else update();
      $("connection").textContent = "Connected";
    } catch {
      $("connection").textContent = "Disconnected · draft kept locally";
    } finally {
      polling = false;
    }
  }, 1500);
}
boot().catch(error);
