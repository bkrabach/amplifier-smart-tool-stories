// Standalone presentation controls. No service, model, or network access.
(() => {
  const slides = [...document.querySelectorAll('.slide')];
  if (!slides.length) return;
  const dimensions = slides.map(s => {
    const c = getComputedStyle(s);
    return {width: s.offsetWidth || 1280, height: s.offsetHeight || 720,
      display: c.display === 'none' ? (c.flexDirection === 'column' ? 'flex' : 'block') : c.display};
  });
  const style = document.createElement('style');
  style.textContent = `@media screen{html,body{margin:0!important;padding:0!important;width:100%;height:100%;overflow:hidden!important;background:#18212b!important}.slide{display:none!important}.slide[data-stories-present]{display:var(--presentation-display)!important;position:fixed!important;left:50%!important;top:calc((100vh - 56px)/2)!important;margin:0!important;box-sizing:border-box!important;width:var(--presentation-width)!important;height:var(--presentation-height)!important;min-height:0!important;opacity:1!important;visibility:visible!important;transform:translate(-50%,-50%) scale(var(--presentation-scale))!important;transform-origin:center!important}#stories-presentation-controls{position:fixed;bottom:8px;left:50%;transform:translateX(-50%);display:flex;align-items:center;gap:14px;padding:6px 12px;border-radius:24px;background:#18212b;color:white;font:16px system-ui;z-index:2147483647}#stories-presentation-controls button{font:inherit;border:1px solid #718096;border-radius:16px;background:#253445;color:white;padding:5px 14px;cursor:pointer}#stories-presentation-controls button:disabled{opacity:.4;cursor:default}}@media print{#stories-presentation-controls{display:none!important}.slide{display:var(--presentation-display,block)!important;position:relative!important;transform:none!important;page-break-after:always}}`;
  document.head.append(style);
  const controls = document.createElement('nav');
  controls.id = 'stories-presentation-controls';
  controls.setAttribute('aria-label','Presentation navigation');
  controls.innerHTML = '<button type="button" aria-label="Previous slide">←</button><span aria-live="polite"></span><button type="button" aria-label="Next slide">→</button>';
  document.body.append(controls);
  const [previous,next] = controls.querySelectorAll('button');
  const counter = controls.querySelector('span');
  let index = 0;
  function fit() {
    slides.forEach((s,i) => {
      const d=dimensions[i];
      s.style.setProperty('--presentation-display',d.display);
      s.style.setProperty('--presentation-width',d.width+'px');
      s.style.setProperty('--presentation-height',d.height+'px');
      s.style.setProperty('--presentation-scale',Math.min(innerWidth/d.width,Math.max(1,innerHeight-56)/d.height));
    });
  }
  function show(target) {
    index=Math.max(0,Math.min(target,slides.length-1));
    slides.forEach((s,i) => {
      s.toggleAttribute('data-stories-present',i===index);
      if(i!==index) s.querySelectorAll('video,audio').forEach(m=>m.pause());
    });
    counter.textContent=`${index+1} / ${slides.length}`;
    previous.disabled=index===0;next.disabled=index===slides.length-1;
  }
  previous.onclick=()=>show(index-1);next.onclick=()=>show(index+1);
  document.addEventListener('keydown',e=>{
    if(e.altKey||e.ctrlKey||e.metaKey||e.target.closest('input,textarea,select,button,video,audio,[contenteditable]')) return;
    const targets={ArrowRight:index+1,ArrowDown:index+1,PageDown:index+1,' ':index+1,ArrowLeft:index-1,ArrowUp:index-1,PageUp:index-1,Home:0,End:slides.length-1};
    if(e.key in targets){e.preventDefault();show(targets[e.key]);}
  });
  addEventListener('resize',fit);fit();show(0);
})();
