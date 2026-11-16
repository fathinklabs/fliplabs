/**
 * FlipLabs HTML5 3D FlipBook Viewer Controller
 * Supports Double-Page Spread (Desktop) & Single-Page (Mobile),
 * Multi-tier WebP loading, Full-Text Search with yellow coordinate highlights,
 * Hierarchical TOC, Thumbnail Tray, Annotations/Highlighter, Bookmarks,
 * FlipShot export, Share/Iframe Embed, AI Assistant, and License Tier enforcement.
 */

const state = {
  bookId: 'smp8-matematika',
  config: null,
  toc: [],
  searchIndex: null,
  currentPage: 1,
  totalPages: 1,
  doublePageMode: window.innerWidth > 900,
  zoom: 1,
  panX: 0,
  panY: 0,
  isDraggingPan: false,
  dragStartX: 0,
  dragStartY: 0,
  autoPlayTimer: null,
  searchQuery: '',
  annoActive: false,
  annoTool: 'highlighter', // 'highlighter' | 'pen' | 'eraser'
  annoColor: 'rgba(250, 204, 21, 0.42)',
  bookmarks: [],
};

function getBookIdFromUrl() {
  const params = new URLSearchParams(window.location.search);
  if (params.get('book')) return params.get('book');
  const pathMatch = window.location.pathname.match(/\/view\/([^\/]+)/);
  if (pathMatch) return pathMatch[1];
  return 'smp8-matematika';
}

function getPageFromHash() {
  const m = window.location.hash.match(/#p=(\d+)/i);
  return m ? Math.max(1, parseInt(m[1], 10)) : 1;
}

function setHashPage(pageNum) {
  history.replaceState(null, '', `#p=${pageNum}`);
}

function showToast(msg) {
  const el = document.getElementById('toastMsg');
  if (!el) return;
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => el.classList.remove('show'), 2600);
}

async function initViewer() {
  state.bookId = getBookIdFromUrl();
  state.currentPage = getPageFromHash();

  try {
    const base = `/books/${state.bookId}`;
    const [cfgRes, tocRes, idxRes] = await Promise.all([
      fetch(`${base}/book-config.json`),
      fetch(`${base}/toc.json`),
      fetch(`${base}/search-index.json`),
    ]);

    if (!cfgRes.ok) throw new Error('Buku tidak ditemukan');
    state.config = await cfgRes.json();
    state.toc = tocRes.ok ? await tocRes.json() : [];
    state.searchIndex = idxRes.ok ? await idxRes.json() : { pages: [] };
    state.totalPages = state.config.totalPageCount || 1;
    state.currentPage = Math.min(Math.max(1, state.currentPage), state.totalPages);

    loadBookmarks();
    applyBrandingAndTheme();
    applyLicenseTier(state.config.licenseTier || 'enterprise');
    renderTOC();
    renderThumbnails();
    renderBookmarks();
    layoutSpread();
    renderCurrentPages(false);
    bindEvents();
  } catch (err) {
    console.error(err);
    showToast('Gagal memuat data buku: ' + err.message);
  }
}

function applyBrandingAndTheme() {
  const cfg = state.config;
  document.title = `${cfg.title} — FlipLabs Viewer`;
  document.getElementById('bookTitle').textContent = cfg.title;
  document.getElementById('bookSubtitle').textContent = `${cfg.author} • ${cfg.category || ''}`;
  document.getElementById('totalPageLabel').textContent = `/ ${state.totalPages}`;

  if (cfg.security && cfg.security.disableRightClick) {
    document.addEventListener('contextmenu', (e) => e.preventDefault());
  }
}

function applyLicenseTier(tier) {
  tier = (tier || 'enterprise').toLowerCase();
  state.config.licenseTier = tier;

  const badge = document.getElementById('licenseBadge');
  badge.className = `license-badge ${tier}`;
  badge.textContent = `PLAN: ${tier.toUpperCase()}`;

  const tierSelect = document.getElementById('tierSwitcher');
  if (tierSelect) tierSelect.value = tier;

  // Enforce feature matrix per tier
  const rules = {
    basic: {
      download: false,
      print: false,
      annotations: false,
      bookmarks: false,
      flipshot: false,
      ai: false,
    },
    pro: {
      download: true,
      print: true,
      annotations: true,
      bookmarks: true,
      flipshot: true,
      ai: false,
    },
    enterprise: {
      download: true,
      print: true,
      annotations: true,
      bookmarks: true,
      flipshot: true,
      ai: true,
    },
  }[tier] || {};

  setButtonLock('btnDownload', !rules.download, 'Fitur Download PDF memerlukan lisensi PRO / ENTERPRISE');
  setButtonLock('btnPrint', !rules.print, 'Fitur Cetak memerlukan lisensi PRO / ENTERPRISE');
  setButtonLock('btnAnnotate', !rules.annotations, 'Fitur Stabilo & Anotasi memerlukan lisensi PRO / ENTERPRISE');
  setButtonLock('btnBookmark', !rules.bookmarks, 'Fitur Penanda Halaman memerlukan lisensi PRO / ENTERPRISE');
  setButtonLock('btnFlipShot', !rules.flipshot, 'Fitur FlipShot Screenshot memerlukan lisensi PRO / ENTERPRISE');
  setButtonLock('btnAIChat', !rules.ai, 'Fitur AI Book Assistant khusus lisensi ENTERPRISE');
}

function setButtonLock(btnId, isLocked, lockReason) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.dataset.locked = isLocked ? 'true' : 'false';
  btn.dataset.lockReason = lockReason || '';
  btn.classList.toggle('locked', isLocked);
}

function checkLock(btnId) {
  const btn = document.getElementById(btnId);
  if (btn && btn.dataset.locked === 'true') {
    showToast('🔒 ' + (btn.dataset.lockReason || 'Fitur terkunci pada paket lisensi ini'));
    return true;
  }
  return false;
}

/**
 * Compute which pages are shown on left and right slots
 */
function getSpreadPages(page) {
  const isMobile = window.innerWidth <= 860;
  const doubleMode = state.doublePageMode && !isMobile;

  if (!doubleMode || page === 1 || (page === state.totalPages && state.totalPages % 2 === 0)) {
    return { mode: 'single', left: null, right: page };
  }
  // Spread pairs: (2,3), (4,5), (6,7)...
  const leftPage = page % 2 === 0 ? page : page - 1;
  const rightPage = leftPage + 1 <= state.totalPages ? leftPage + 1 : null;
  if (!rightPage) {
    return { mode: 'single', left: null, right: leftPage };
  }
  return { mode: 'double', left: leftPage, right: rightPage };
}

function layoutSpread() {
  const stage = document.getElementById('stageViewport');
  const spread = document.getElementById('bookSpread');
  const leftSlot = document.getElementById('leftPageSlot');
  const rightSlot = document.getElementById('rightPageSlot');
  const spine = document.getElementById('spineShadow');

  const availW = stage.clientWidth - 96;
  const availH = stage.clientHeight - 36;
  const ratio = state.config ? state.config.pageRatio || 1.4142 : 1.4142;

  const spreadInfo = getSpreadPages(state.currentPage);

  let pageH = availH;
  let pageW = Math.floor(pageH / ratio);

  if (spreadInfo.mode === 'double') {
    if (pageW * 2 > availW) {
      pageW = Math.floor(availW / 2);
      pageH = Math.floor(pageW * ratio);
    }
    leftSlot.style.display = 'block';
    leftSlot.style.width = `${pageW}px`;
    leftSlot.style.height = `${pageH}px`;
    rightSlot.style.width = `${pageW}px`;
    rightSlot.style.height = `${pageH}px`;
    spread.style.width = `${pageW * 2}px`;
    spread.style.height = `${pageH}px`;
    spine.style.display = 'block';
  } else {
    if (pageW > availW) {
      pageW = Math.floor(availW);
      pageH = Math.floor(pageW * ratio);
    }
    leftSlot.style.display = 'none';
    rightSlot.style.width = `${pageW}px`;
    rightSlot.style.height = `${pageH}px`;
    spread.style.width = `${pageW}px`;
    spread.style.height = `${pageH}px`;
    spine.style.display = 'none';
  }
}

function getPageImageUrl(pageNum) {
  const tierFolder = window.innerWidth <= 768 && state.zoom <= 1.1 ? 'mobile' : 'large';
  return `/books/${state.bookId}/files/${tierFolder}/${pageNum}.webp`;
}

function renderCurrentPages(direction) {
  layoutSpread();
  const spread = document.getElementById('bookSpread');
  const spreadInfo = getSpreadPages(state.currentPage);

  if (direction) {
    spread.classList.remove('flipping-next', 'flipping-prev');
    void spread.offsetWidth; // force reflow
    spread.classList.add(direction === 'next' ? 'flipping-next' : 'flipping-prev');
    window.flipSound.playFlip();
  }

  const leftImg = document.getElementById('leftPageImg');
  const rightImg = document.getElementById('rightPageImg');

  if (spreadInfo.mode === 'double') {
    leftImg.src = getPageImageUrl(spreadInfo.left);
    rightImg.src = getPageImageUrl(spreadInfo.right);
    document.getElementById('pageInput').value = `${spreadInfo.left}-${spreadInfo.right}`;
    renderHighlightsForSlot('leftHighlightLayer', spreadInfo.left);
    renderHighlightsForSlot('rightHighlightLayer', spreadInfo.right);
    loadAnnotationForCanvas('leftAnnoCanvas', spreadInfo.left);
    loadAnnotationForCanvas('rightAnnoCanvas', spreadInfo.right);
  } else {
    rightImg.src = getPageImageUrl(spreadInfo.right);
    document.getElementById('pageInput').value = `${spreadInfo.right}`;
    renderHighlightsForSlot('rightHighlightLayer', spreadInfo.right);
    loadAnnotationForCanvas('rightAnnoCanvas', spreadInfo.right);
  }

  // Preload adjacent pages
  for (let d = 1; d <= 2; d++) {
    if (state.currentPage + d <= state.totalPages) {
      const pre = new Image();
      pre.src = getPageImageUrl(state.currentPage + d);
    }
  }

  // Update buttons & active states
  document.getElementById('btnPrevStage').disabled = state.currentPage <= 1;
  document.getElementById('btnNextStage').disabled = state.currentPage >= state.totalPages;
  setHashPage(state.currentPage);
  highlightActiveTOCAndThumb();
}

function goToPage(targetPage, dir) {
  targetPage = Math.max(1, Math.min(state.totalPages, targetPage));
  if (targetPage === state.currentPage) return;
  const direction = dir || (targetPage > state.currentPage ? 'next' : 'prev');
  state.currentPage = targetPage;
  renderCurrentPages(direction);
}

function stepNext() {
  const info = getSpreadPages(state.currentPage);
  const step = info.mode === 'double' ? 2 : 1;
  const nextP = info.mode === 'double' ? info.left + step : state.currentPage + 1;
  if (nextP <= state.totalPages) {
    goToPage(nextP, 'next');
  } else if (state.currentPage < state.totalPages) {
    goToPage(state.totalPages, 'next');
  }
}

function stepPrev() {
  const info = getSpreadPages(state.currentPage);
  if (info.mode === 'double') {
    goToPage(Math.max(1, info.left - 2), 'prev');
  } else {
    goToPage(Math.max(1, state.currentPage - 1), 'prev');
  }
}

/* Table of Contents */
function renderTOC() {
  const container = document.getElementById('tocList');
  container.innerHTML = '';

  function appendItems(items, level = 1) {
    items.forEach((item) => {
      const row = document.createElement('div');
      row.className = `toc-item level-${level}`;
      row.dataset.page = item.page;
      row.innerHTML = `
        <span>${item.title}</span>
        <span class="toc-page-badge">Hal. ${item.page}</span>
      `;
      row.addEventListener('click', () => {
        goToPage(item.page);
        if (window.innerWidth <= 768) toggleDrawer('tocDrawer', false);
      });
      container.appendChild(row);
      if (item.children && item.children.length) {
        appendItems(item.children, level + 1);
      }
    });
  }
  appendItems(state.toc);
}

/* Bottom Thumbnail Tray */
function renderThumbnails() {
  const tray = document.getElementById('thumbTray');
  tray.innerHTML = '';
  for (let p = 1; p <= state.totalPages; p++) {
    const card = document.createElement('div');
    card.className = 'thumb-card';
    card.dataset.page = p;
    card.innerHTML = `
      <img src="/books/${state.bookId}/files/thumb/${p}.webp" loading="lazy" alt="Hal ${p}">
      <span>Hal. ${p}</span>
    `;
    card.addEventListener('click', () => goToPage(p));
    tray.appendChild(card);
  }
}

function highlightActiveTOCAndThumb() {
  document.querySelectorAll('.thumb-card').forEach((el) => {
    const p = parseInt(el.dataset.page, 10);
    el.classList.toggle('active', p === state.currentPage);
  });
  document.querySelectorAll('.toc-item').forEach((el) => {
    const p = parseInt(el.dataset.page, 10);
    el.classList.toggle('active', p === state.currentPage);
  });
}

/* Full-Text Search & Coordinate Box Highlighting */
function performSearch(query) {
  state.searchQuery = (query || '').trim();
  const resContainer = document.getElementById('searchResults');
  resContainer.innerHTML = '';

  renderCurrentPages(false);

  if (state.searchQuery.length < 2) {
    resContainer.innerHTML = '<div style="color:var(--text-muted);font-size:12.5px;padding:8px;">Ketik minimal 2 huruf untuk mencari rumus, bab, atau konsep di dalam buku...</div>';
    return;
  }

  const qLower = state.searchQuery.toLowerCase();
  const pages = (state.searchIndex && state.searchIndex.pages) || [];
  let hitCount = 0;

  pages.forEach((pObj) => {
    const txt = pObj.text || '';
    const idx = txt.toLowerCase().indexOf(qLower);
    if (idx !== -1) {
      hitCount++;
      const start = Math.max(0, idx - 40);
      const end = Math.min(txt.length, idx + state.searchQuery.length + 60);
      let snippet = txt.slice(start, end);
      const regex = new RegExp(`(${state.searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
      snippet = snippet.replace(regex, '<mark>$1</mark>');

      const card = document.createElement('div');
      card.className = 'search-result-card';
      card.innerHTML = `
        <div style="display:flex;justify-content:space-between;font-size:12px;font-weight:700;color:var(--accent-hover);">
          <span>Halaman ${pObj.page}</span>
          <span>Lihat & Sorot →</span>
        </div>
        <div class="search-snippet">...${snippet}...</div>
      `;
      card.addEventListener('click', () => {
        goToPage(pObj.page);
      });
      resContainer.appendChild(card);
    }
  });

  if (hitCount === 0) {
    resContainer.innerHTML = `<div style="color:var(--text-muted);font-size:12.5px;padding:8px;">Tidak ditemukan kata <b>"${state.searchQuery}"</b>.</div>`;
  }
}

function renderHighlightsForSlot(layerId, pageNum) {
  const layer = document.getElementById(layerId);
  if (!layer) return;
  layer.innerHTML = '';
  if (!state.searchQuery || state.searchQuery.length < 2 || !state.searchIndex) return;

  const qLower = state.searchQuery.toLowerCase();
  const pageData = (state.searchIndex.pages || []).find((p) => p.page === pageNum);
  if (!pageData || !pageData.words) return;

  pageData.words.forEach((wObj) => {
    if (wObj.w.toLowerCase().includes(qLower)) {
      const box = document.createElement('div');
      box.className = 'search-hit-box';
      box.style.left = `${wObj.x}%`;
      box.style.top = `${wObj.y}%`;
      box.style.width = `${Math.max(wObj.width, 2)}%`;
      box.style.height = `${Math.max(wObj.height, 1.8)}%`;
      layer.appendChild(box);
    }
  });
}

/* Annotations & Highlighter Canvas */
function setupAnnotationCanvas(canvasId, getPageNumFn) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let drawing = false;

  function getPos(e) {
    const rect = canvas.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    return {
      x: ((clientX - rect.left) / rect.width) * canvas.width,
      y: ((clientY - rect.top) / rect.height) * canvas.height,
    };
  }

  function start(e) {
    if (!state.annoActive) return;
    drawing = true;
    const pos = getPos(e);
    ctx.beginPath();
    ctx.moveTo(pos.x, pos.y);
  }

  function move(e) {
    if (!drawing || !state.annoActive) return;
    e.preventDefault();
    const pos = getPos(e);
    if (state.annoTool === 'eraser') {
      ctx.globalCompositeOperation = 'destination-out';
      ctx.lineWidth = 26;
    } else if (state.annoTool === 'highlighter') {
      ctx.globalCompositeOperation = 'source-over';
      ctx.strokeStyle = 'rgba(250, 204, 21, 0.35)';
      ctx.lineWidth = 20;
      ctx.lineCap = 'round';
    } else {
      ctx.globalCompositeOperation = 'source-over';
      ctx.strokeStyle = '#ef4444';
      ctx.lineWidth = 3.5;
      ctx.lineCap = 'round';
    }
    ctx.lineTo(pos.x, pos.y);
    ctx.stroke();
  }

  function stop() {
    if (!drawing) return;
    drawing = false;
    const pageNum = getPageNumFn();
    if (pageNum) {
      localStorage.setItem(`fliplabs_anno_${state.bookId}_p${pageNum}`, canvas.toDataURL());
    }
  }

  canvas.addEventListener('mousedown', start);
  canvas.addEventListener('mousemove', move);
  window.addEventListener('mouseup', stop);
  canvas.addEventListener('touchstart', start, { passive: false });
  canvas.addEventListener('touchmove', move, { passive: false });
  canvas.addEventListener('touchend', stop);
}

function loadAnnotationForCanvas(canvasId, pageNum) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  canvas.width = 800;
  canvas.height = 1131;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const saved = localStorage.getItem(`fliplabs_anno_${state.bookId}_p${pageNum}`);
  if (saved) {
    const img = new Image();
    img.onload = () => ctx.drawImage(img, 0, 0);
    img.src = saved;
  }
}

/* Bookmarks */
function loadBookmarks() {
  try {
    const raw = localStorage.getItem(`fliplabs_bm_${state.bookId}`);
    state.bookmarks = raw ? JSON.parse(raw) : [];
  } catch (e) {
    state.bookmarks = [];
  }
}

function toggleCurrentBookmark() {
  const idx = state.bookmarks.findIndex((b) => b.page === state.currentPage);
  if (idx >= 0) {
    state.bookmarks.splice(idx, 1);
    showToast(`Penanda Halaman ${state.currentPage} dihapus`);
  } else {
    state.bookmarks.push({
      page: state.currentPage,
      label: `Halaman ${state.currentPage}`,
      time: new Date().toLocaleDateString('id-ID'),
    });
    showToast(`🔖 Halaman ${state.currentPage} ditambahkan ke Penanda Buku`);
  }
  localStorage.setItem(`fliplabs_bm_${state.bookId}`, JSON.stringify(state.bookmarks));
  renderBookmarks();
}

function renderBookmarks() {
  const list = document.getElementById('bookmarkList');
  if (!list) return;
  list.innerHTML = '';
  if (!state.bookmarks.length) {
    list.innerHTML = '<div style="color:var(--text-muted);font-size:12.5px;padding:8px;">Belum ada halaman yang ditandai. Klik tombol "+ Tandai Halaman Aktif" di atas.</div>';
    return;
  }
  state.bookmarks.forEach((bm) => {
    const item = document.createElement('div');
    item.className = 'toc-item';
    item.innerHTML = `
      <span>🔖 ${bm.label} <small style="color:var(--text-muted)">(${bm.time})</small></span>
      <span class="toc-page-badge">Buka</span>
    `;
    item.addEventListener('click', () => goToPage(bm.page));
    list.appendChild(item);
  });
}

/* Zoom & Pan */
function setZoom(newZoom) {
  state.zoom = Math.max(1, Math.min(2.6, newZoom));
  if (state.zoom === 1) {
    state.panX = 0;
    state.panY = 0;
  }
  updateZoomTransform();
}

function updateZoomTransform() {
  const layer = document.getElementById('bookZoomLayer');
  layer.style.transform = `translate(${state.panX}px, ${state.panY}px) scale(${state.zoom})`;
}

/* FlipShot (Download Current Page Snapshot PNG) */
function captureFlipShot() {
  if (checkLock('btnFlipShot')) return;
  const img = document.getElementById('rightPageImg');
  const canvas = document.createElement('canvas');
  canvas.width = img.naturalWidth || 1000;
  canvas.height = img.naturalHeight || 1414;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(img, 0, 0);

  // Add Labschool attribution footer
  ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
  ctx.fillRect(0, canvas.height - 46, canvas.width, 46);
  ctx.fillStyle = '#38bdf8';
  ctx.font = 'bold 18px sans-serif';
  ctx.fillText(`FlipShot • ${state.config.title} (Hal. ${state.currentPage}) — books.labschool.xyz`, 20, canvas.height - 17);

  const link = document.createElement('a');
  link.download = `FlipShot-${state.bookId}-Hal-${state.currentPage}.png`;
  link.href = canvas.toDataURL('image/png');
  link.click();
  showToast('📸 FlipShot halaman berhasil diunduh sebagai PNG!');
}

/* AI Book Assistant */
async function sendAIChatQuestion() {
  const input = document.getElementById('aiChatInput');
  const msgBox = document.getElementById('aiChatMessages');
  const q = (input.value || '').trim();
  if (!q) return;
  input.value = '';

  const userDiv = document.createElement('div');
  userDiv.className = 'chat-bubble user';
  userDiv.textContent = q;
  msgBox.appendChild(userDiv);
  msgBox.scrollTop = msgBox.scrollHeight;

  const aiDiv = document.createElement('div');
  aiDiv.className = 'chat-bubble ai';
  aiDiv.textContent = 'Menganalisis isi halaman buku...';
  msgBox.appendChild(aiDiv);

  try {
    const res = await fetch('/api/ai-chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        bookId: state.bookId,
        currentPage: state.currentPage,
        question: q,
      }),
    });
    if (res.ok) {
      const data = await res.json();
      aiDiv.innerHTML = data.answer;
    } else {
      throw new Error('Fallback local search');
    }
  } catch (e) {
    // Client-side smart textbook context responder fallback
    const pages = (state.searchIndex && state.searchIndex.pages) || [];
    const curPageObj = pages.find((p) => p.page === state.currentPage) || pages[0];
    aiDiv.innerHTML = `<b>Referensi Halaman ${state.currentPage}:</b><br>${(curPageObj && curPageObj.text.slice(0, 320)) || 'Silakan gunakan fitur pencarian untuk menemukan topik terkait.'}...`;
  }
  msgBox.scrollTop = msgBox.scrollHeight;
}

function toggleDrawer(drawerId, forceState) {
  ['tocDrawer', 'searchDrawer', 'bookmarkDrawer', 'aiDrawer'].forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    if (id === drawerId) {
      const next = forceState !== undefined ? forceState : !el.classList.contains('open');
      el.classList.toggle('open', next);
    } else {
      el.classList.remove('open');
    }
  });
}

function bindEvents() {
  window.addEventListener('resize', () => renderCurrentPages(false));

  // Navigation buttons
  document.getElementById('btnPrevStage').addEventListener('click', stepPrev);
  document.getElementById('btnNextStage').addEventListener('click', stepNext);
  document.getElementById('btnFirstPage').addEventListener('click', () => goToPage(1, 'prev'));
  document.getElementById('btnPrevPage').addEventListener('click', stepPrev);
  document.getElementById('btnNextPage').addEventListener('click', stepNext);
  document.getElementById('btnLastPage').addEventListener('click', () => goToPage(state.totalPages, 'next'));

  document.getElementById('cornerLeft').addEventListener('click', stepPrev);
  document.getElementById('cornerRight').addEventListener('click', stepNext);

  // Page direct input
  document.getElementById('pageInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const val = parseInt(e.target.value, 10);
      if (!isNaN(val)) goToPage(val);
    }
  });

  // Keyboard shortcuts
  window.addEventListener('keydown', (e) => {
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) return;
    if (e.key === 'ArrowRight') stepNext();
    else if (e.key === 'ArrowLeft') stepPrev();
    else if (e.key === '+' || e.key === '=') setZoom(state.zoom + 0.25);
    else if (e.key === '-') setZoom(state.zoom - 0.25);
    else if (e.key === '0') setZoom(1);
  });

  // Touch swipe on mobile/tablet
  let touchStartX = 0;
  const stage = document.getElementById('stageViewport');
  stage.addEventListener('touchstart', (e) => {
    if (state.annoActive || state.zoom > 1.05) return;
    touchStartX = e.changedTouches[0].screenX;
  }, { passive: true });
  stage.addEventListener('touchend', (e) => {
    if (state.annoActive || state.zoom > 1.05) return;
    const dx = e.changedTouches[0].screenX - touchStartX;
    if (dx < -45) stepNext();
    else if (dx > 45) stepPrev();
  }, { passive: true });

  // Mouse pan when zoomed
  const zoomLayer = document.getElementById('bookZoomLayer');
  stage.addEventListener('mousedown', (e) => {
    if (state.zoom <= 1.02 || state.annoActive) return;
    state.isDraggingPan = true;
    state.dragStartX = e.clientX - state.panX;
    state.dragStartY = e.clientY - state.panY;
    zoomLayer.classList.add('dragging');
  });
  window.addEventListener('mousemove', (e) => {
    if (!state.isDraggingPan) return;
    state.panX = e.clientX - state.dragStartX;
    state.panY = e.clientY - state.dragStartY;
    updateZoomTransform();
  });
  window.addEventListener('mouseup', () => {
    state.isDraggingPan = false;
    zoomLayer.classList.remove('dragging');
  });

  // Toolbar triggers
  document.getElementById('btnTOC').addEventListener('click', () => toggleDrawer('tocDrawer'));
  document.getElementById('btnSearch').addEventListener('click', () => {
    toggleDrawer('searchDrawer');
    setTimeout(() => document.getElementById('searchInput').focus(), 150);
  });
  document.getElementById('btnThumbnails').addEventListener('click', () => {
    document.getElementById('thumbTray').classList.toggle('open');
  });
  document.getElementById('btnPageMode').addEventListener('click', () => {
    state.doublePageMode = !state.doublePageMode;
    showToast(state.doublePageMode ? '📖 Mode Dua Halaman (Double Spread)' : '📄 Mode Satu Halaman (Single Page)');
    renderCurrentPages(false);
  });
  document.getElementById('btnZoomIn').addEventListener('click', () => setZoom(state.zoom + 0.3));
  document.getElementById('btnZoomOut').addEventListener('click', () => setZoom(state.zoom - 0.3));

  document.getElementById('btnSound').addEventListener('click', (e) => {
    const on = window.flipSound.toggleFlipSound();
    e.currentTarget.classList.toggle('active', on);
    showToast(on ? '🔊 Suara Lembaran Kertas: Aktif' : '🔇 Suara Lembaran Kertas: Nonaktif');
  });

  document.getElementById('btnAutoPlay').addEventListener('click', (e) => {
    if (state.autoPlayTimer) {
      clearInterval(state.autoPlayTimer);
      state.autoPlayTimer = null;
      e.currentTarget.classList.remove('active');
      showToast('⏸ Slideshow Otomatis Dihentikan');
    } else {
      e.currentTarget.classList.add('active');
      showToast('▶ Slideshow Otomatis Dimulai (Setiap 3.5 detik)');
      state.autoPlayTimer = setInterval(() => {
        if (state.currentPage >= state.totalPages) goToPage(1, 'prev');
        else stepNext();
      }, 3500);
    }
  });

  document.getElementById('btnBookmark').addEventListener('click', () => {
    if (checkLock('btnBookmark')) return;
    toggleDrawer('bookmarkDrawer');
  });
  document.getElementById('btnAddBookmark').addEventListener('click', toggleCurrentBookmark);

  document.getElementById('btnAnnotate').addEventListener('click', (e) => {
    if (checkLock('btnAnnotate')) return;
    state.annoActive = !state.annoActive;
    e.currentTarget.classList.toggle('active', state.annoActive);
    document.getElementById('annotationBar').classList.toggle('open', state.annoActive);
    document.getElementById('leftAnnoCanvas').classList.toggle('active', state.annoActive);
    document.getElementById('rightAnnoCanvas').classList.toggle('active', state.annoActive);
    showToast(state.annoActive ? '🖍 Mode Stabilo & Coretan Aktif' : 'Mode Baca Normal');
  });

  document.querySelectorAll('.anno-chip[data-tool]').forEach((chip) => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('.anno-chip[data-tool]').forEach((c) => c.classList.remove('active'));
      chip.classList.add('active');
      state.annoTool = chip.dataset.tool;
    });
  });

  document.getElementById('btnClearAnno').addEventListener('click', () => {
    const info = getSpreadPages(state.currentPage);
    [info.left, info.right].forEach((p) => {
      if (p) localStorage.removeItem(`fliplabs_anno_${state.bookId}_p${p}`);
    });
    renderCurrentPages(false);
    showToast('Coretan pada halaman ini dibersihkan');
  });

  setupAnnotationCanvas('leftAnnoCanvas', () => getSpreadPages(state.currentPage).left);
  setupAnnotationCanvas('rightAnnoCanvas', () => getSpreadPages(state.currentPage).right);

  document.getElementById('btnFlipShot').addEventListener('click', captureFlipShot);

  document.getElementById('btnDownload').addEventListener('click', () => {
    if (checkLock('btnDownload')) return;
    window.open(`/books/${state.bookId}/files/book.pdf`, '_blank');
  });

  document.getElementById('btnPrint').addEventListener('click', () => {
    if (checkLock('btnPrint')) return;
    window.open(`/books/${state.bookId}/files/book.pdf`, '_blank');
  });

  document.getElementById('btnShare').addEventListener('click', () => {
    const url = `${window.location.origin}/view/${state.bookId}#p=${state.currentPage}`;
    document.getElementById('shareDirectLink').value = url;
    document.getElementById('shareEmbedCode').value = `<iframe src="${url}" width="100%" height="650" frameborder="0" allowfullscreen></iframe>`;
    document.getElementById('shareModal').classList.add('open');
  });

  document.getElementById('btnFullscreen').addEventListener('click', () => {
    if (!document.fullscreenElement) document.documentElement.requestFullscreen();
    else document.exitFullscreen();
  });

  document.getElementById('btnAIChat').addEventListener('click', () => {
    if (checkLock('btnAIChat')) return;
    toggleDrawer('aiDrawer');
  });

  document.getElementById('btnSendAI').addEventListener('click', sendAIChatQuestion);
  document.getElementById('aiChatInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendAIChatQuestion();
  });

  document.getElementById('searchInput').addEventListener('input', (e) => {
    performSearch(e.target.value);
  });

  // Live License Tier Switcher for Demo/Testing
  const tierSwitcher = document.getElementById('tierSwitcher');
  if (tierSwitcher) {
    tierSwitcher.addEventListener('change', (e) => {
      applyLicenseTier(e.target.value);
      showToast(`Simulasi Lisensi Diubah ke: ${e.target.value.toUpperCase()}`);
    });
  }
}

document.addEventListener('DOMContentLoaded', initViewer);
