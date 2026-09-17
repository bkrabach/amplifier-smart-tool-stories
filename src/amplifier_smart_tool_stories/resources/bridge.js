// Runs only in the opaque material frame. It has no dashboard token or API access.
(() => {
  const channel = __CHANNEL__;
  const emit = (type, data = {}) =>
    parent.postMessage({ channel, type, ...data }, "*");
  let overlay = true,
    slide = 0,
    noteRanges = [];
  const slides = [...document.querySelectorAll(".slide")];
  for (const slide of slides) {
    const computed = getComputedStyle(slide);
    const display =
      computed.display === "none"
        ? computed.flexDirection === "column"
          ? "flex"
          : "block"
        : computed.display;
    slide.style.setProperty("--stories-display", display);
  }
  const style = document.createElement("style");
  style.textContent = `html,body{margin:0;min-height:100%;}body{padding:0!important}.slide{box-sizing:border-box!important;display:none!important;min-height:100vh!important;width:100%!important}.slide.stories-current{display:var(--stories-display,block)!important;position:relative!important;opacity:1!important;visibility:visible!important;transform:none!important}::highlight(stories){background:#f8d36b75;text-decoration:underline}::highlight(selectionTarget){background:#92c5ff80}[data-stories-selected]{outline:2px solid #95bde8!important;outline-offset:3px}[data-stories-agent]{outline:2px solid #f8d36b!important;outline-offset:3px}nav,.nav-dots,.slide-counter,.navigation{display:none!important}body{user-select:text!important}*{user-select:text}.stories-current{pointer-events:auto!important}`;
  document.head.append(style);
  const element = (id) =>
    [...document.querySelectorAll("[data-stories-id]")].find(
      (e) => e.dataset.storiesId === id,
    );
  const chars = (s) => Array.from(s).length;
  function textRange(a) {
    const el = element(a.element);
    if (!el) return null;
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    let n,
      start = a.start,
      end = a.end,
      r = document.createRange(),
      set = false;
    while ((n = walker.nextNode())) {
      let count = chars(n.textContent);
      if (!set && start <= count) {
        r.setStart(
          n,
          Array.from(n.textContent).slice(0, start).join("").length,
        );
        set = true;
      }
      if (set && end <= count) {
        r.setEnd(n, Array.from(n.textContent).slice(0, end).join("").length);
        return r;
      }
      if (!set) start -= count;
      end -= count;
    }
    return null;
  }
  function show(i) {
    if (slides.length) {
      slide = Math.max(0, Math.min(i, slides.length - 1));
      slides.forEach((s, j) =>
        s.classList.toggle("stories-current", j === slide),
      );
    }
    emit("position", {
      slide,
      total: slides.length || 1,
      elements: slides[slide]
        ? [
            slides[slide],
            ...slides[slide].querySelectorAll("[data-stories-id]"),
          ]
            .map((el) => el.dataset.storiesId)
            .filter(Boolean)
        : null,
    });
  }
  function clear() {
    document
      .querySelectorAll("[data-stories-selected]")
      .forEach((e) => e.removeAttribute("data-stories-selected"));
    if (CSS.highlights) CSS.highlights.delete("selectionTarget");
  }
  let dragging = false,
    down;
  document.addEventListener("pointerdown", (e) => {
    down = { x: e.clientX, y: e.clientY };
    dragging = false;
  });
  document.addEventListener("pointermove", (e) => {
    if (down && Math.hypot(e.clientX - down.x, e.clientY - down.y) > 4)
      dragging = true;
  });
  document.addEventListener("pointerup", () => {
    down = null;
    if (!overlay) return;
    setTimeout(() => {
      let s = getSelection();
      if (!s || s.isCollapsed || !s.rangeCount) return;
      const r = s.getRangeAt(0);
      let el =
        r.commonAncestorContainer.nodeType === 1
          ? r.commonAncestorContainer
          : r.commonAncestorContainer.parentElement;
      el = el.closest("[data-stories-id]");
      if (!el) return;
      const before = document.createRange();
      before.selectNodeContents(el);
      before.setEnd(r.startContainer, r.startOffset);
      const start = chars(before.toString()),
        quote = r.toString();
      if (!quote.length) return;
      clear();
      if (CSS.highlights)
        CSS.highlights.set("selectionTarget", new Highlight(r.cloneRange()));
      const b = r.getBoundingClientRect();
      emit("selection", {
        anchor: {
          kind: "text",
          element: el.dataset.storiesId,
          start,
          end: start + chars(quote),
          quote,
        },
        rect: { x: b.x, y: b.y, width: b.width, height: b.height },
      });
    }, 0);
  });
  document.addEventListener("click", (e) => {
    if (!overlay || dragging || getSelection()?.toString()) return;
    const hit = noteRanges.find((n) =>
      [...n.range.getClientRects()].some(
        (r) =>
          e.clientX >= r.left &&
          e.clientX <= r.right &&
          e.clientY >= r.top &&
          e.clientY <= r.bottom,
      ),
    );
    if (hit) {
      emit("open-thread", { id: hit.id });
      return;
    }
    const el = e.target.closest("[data-stories-id]");
    if (!el) return;
    e.preventDefault();
    clear();
    el.setAttribute("data-stories-selected", "");
    const b = el.getBoundingClientRect();
    emit("selection", {
      anchor: {
        kind: "element",
        element: el.dataset.storiesId,
        quote: el.textContent.slice(0, 500),
      },
      rect: { x: b.x, y: b.y, width: b.width, height: b.height },
    });
  });
  window.addEventListener("message", (e) => {
    if (e.source !== parent || e.data?.channel !== channel) return;
    const m = e.data;
    if (m.type === "navigate") show(slide + m.delta);
    if (m.type === "position") show(m.slide);
    if (m.type === "overlay") {
      overlay = m.visible;
      clear();
      paint(m.annotations || []);
    }
    if (m.type === "annotations") paint(m.annotations);
    if (m.type === "reveal") {
      const el = element(m.anchor.element);
      if (el) {
        const i = slides.indexOf(el.closest(".slide"));
        if (i >= 0) show(i);
        else el.scrollIntoView({ block: "center" });
        clear();
        el.setAttribute("data-stories-selected", "");
        if (m.anchor.kind === "text" && CSS.highlights) {
          const r = textRange(m.anchor);
          if (r) CSS.highlights.set("selectionTarget", new Highlight(r));
        }
      }
    }
  });
  function paint(notes) {
    noteRanges = [];
    document
      .querySelectorAll("[data-stories-agent]")
      .forEach((e) => e.removeAttribute("data-stories-agent"));
    if (CSS.highlights) CSS.highlights.delete("stories");
    if (!overlay) return;
    const ranges = [];
    for (const n of notes) {
      const a = n.anchor;
      if (a.kind === "text") {
        const r = textRange(a);
        if (r) {
          ranges.push(r);
          noteRanges.push({ id: n.id, range: r });
        }
      } else if (a.kind === "element") {
        element(a.element)?.setAttribute("data-stories-agent", "");
      }
    }
    if (CSS.highlights && ranges.length)
      CSS.highlights.set("stories", new Highlight(...ranges));
  }
  document.addEventListener("keydown", (e) => {
    if (getSelection()?.toString()) return;
    if (e.key === "ArrowRight") show(slide + 1);
    if (e.key === "ArrowLeft") show(slide - 1);
  });
  show(__SLIDE__);
  emit("ready");
})();
