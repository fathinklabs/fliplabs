/**
 * FlipLabs 3D Interactive Book Viewer Engine
 * ------------------------------------------
 * Features:
 * - True Dual-Sided 3D Page Turn Physics (60 FPS requestAnimationFrame + Interactive Drag Peel)
 * - Dynamic Curl Specular Highlight & Cast Shadow on Underlying Page
 * - Password Protected Book Gate + Server-side Verification + Admin Quick-Lock Config
 * - Multi-tier WebP loading, Full-Text Search with yellow coordinate highlights
 * - Hierarchical TOC, Thumbnail Tray, Annotations/Highlighter, Bookmarks, FlipShot, AI Tutor
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
  annoTool: 'highlighter',
  bookmarks: [],
  isFlipping: false,
  isUnlocked: true,
  currentUser: null,
  pageW: 480,
  pageH: 678,
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

function loadUserSession() {
  try {
    const raw = localStorage.getItem('fliplabs_user');
    state.currentUser = raw ? JSON.parse(raw) : null;
  } catch (e) {
    state.currentUser = null;
  }
  const btnLockCfg = document.getElementById('btnQuickPassword');
  if (btnLockCfg) {
    const canManage = state.currentUser && ['admin', 'guru'].includes(state.currentUser.role);
    btnLockCfg.style.display = canManage ? 'inline-flex' : 'none';
  }
}

async function initViewer() {
  state.bookId = getBookIdFromUrl();
  state.currentPage = getPageFromHash();
  loadUserSession();

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
    checkPasswordProtectionGate();
    renderStaticSpread(state.currentPage);
    bindEvents();
  } catch (err) {
    console.error(err);
    showToast('Gagal memuat data buku: ' + err.message);
  }
}

function checkPasswordProtectionGate() {
  const sec = (state.config && state.config.security) || {};
  const sessionKey = `fliplabs_unlocked_${state.bookId}`;
  const alreadyUnlocked = sessionStorage.getItem(sessionKey) === 'true';

  const lockIndicator = document.getElementById('lockStatusBadge');
  if (sec.isPasswordProtected) {
    if (lockIndicator) lockIndicator.style.display = 'inline-flex';
  } else {
    if (lockIndicator) lockIndicator.style.display = 'none';
  }

  if (sec.isPasswordProtected && !alreadyUnlocked) {
    state.isUnlocked = false;
    document.getElementById('stageViewport').classList.add('locked-blur');
    document.getElementById('pwGateBookTitle').textContent = state.config.title;
    document.getElementById('pwGateCover').src = `/books/${state.bookId}/files/shot.jpg`;
    const adminBypassBtn = document.getElementById('btnAdminBypassPw');
    if (adminBypassBtn) {
      adminBypassBtn.style.display =
        state.currentUser && state.currentUser.role === 'admin' ? 'inline-flex' : 'none';
    }
    document.getElementById('passwordGateModal').classList.add('open');
  } else {
    state.isUnlocked = true;
    document.getElementById('stageViewport').classList.remove('locked-blur');
    document.getElementById('passwordGateModal').classList.remove('open');
  }
}

async function submitBookPassword(passwordValue) {
  const errEl = document.getElementById('pwGateError');
  errEl.textContent = '';
  const token = localStorage.getItem('fliplabs_token') || '';

  try {
    const res = await fetch(`/api/books/${state.bookId}/verify-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ password: passwordValue }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Kata sandi salah');

    sessionStorage.setItem(`fliplabs_unlocked_${state.bookId}`, 'true');
    state.isUnlocked = true;
    document.getElementById('stageViewport').classList.remove('locked-blur');
    document.getElementById('passwordGateModal').classList.remove('open');
    showToast('🔓 Akses buku berhasil dibuka!');
  } catch (err) {
    errEl.textContent = '❌ ' + err.message;
  }
}

async function saveBookPasswordConfig() {
  const enabled = document.getElementById('cfgPwEnable').checked;
  const newPw = document.getElementById('cfgPwValue').value.trim();
  const token = localStorage.getItem('fliplabs_token') || '';

  if (enabled && !newPw) {
    showToast('Masukkan kata sandi baru untuk mengaktifkan proteksi');
    return;
  }

  try {
    const res = await fetch(`/api/admin/books/${state.bookId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        title: state.config.title,
        author: state.config.author,
        category: state.config.category || 'SMP Kelas 8',
        subject: state.config.subject || 'Umum',
        licenseTier: state.config.licenseTier || 'enterprise',
        visibility: 'public',
        isPasswordProtected: enabled,
        bookPassword: enabled ? newPw : '',
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal menyimpan proteksi sandi');

    state.config.security.isPasswordProtected = enabled;
    sessionStorage.setItem(`fliplabs_unlocked_${state.bookId}`, 'true');
    document.getElementById('quickPwModal').classList.remove('open');
    checkPasswordProtectionGate();
    showToast(enabled ? '🔒 Proteksi kata sandi buku diaktifkan!' : '🔓 Proteksi kata sandi buku dinonaktifkan');
  } catch (err) {
    showToast('❌ ' + err.message);
  }
}

function applyBrandingAndTheme() {
  const cfg = state.config;
  document.title = `${cfg.title} — FlipLabs 3D Viewer`;
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
  setButtonLock('btnAIChat', !rules.ai, 'Fitur AI Book Tutor khusus lisensi ENTERPRISE');
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

function getSpreadPages(page) {
  const isMobile = window.innerWidth <= 860;
  const doubleMode = state.doublePageMode && !isMobile;

  if (!doubleMode || page === 1 || (page === state.totalPages && state.totalPages % 2 === 0)) {
    return { mode: 'single', left: null, right: page };
  }
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

  const availW = stage.clientWidth - 104;
  const availH = stage.clientHeight - 40;
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

  state.pageW = pageW;
  state.pageH = pageH;
}

function getPageImageUrl(pageNum) {
  const tierFolder = window.innerWidth <= 768 && state.zoom <= 1.1 ? 'mobile' : 'large';
  return `/books/${state.bookId}/files/${tierFolder}/${pageNum}.webp`;
}

function renderStaticSpread(targetPage) {
  state.currentPage = targetPage;
  layoutSpread();
  const spreadInfo = getSpreadPages(targetPage);

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

  for (let d = -2; d <= 4; d++) {
    const targetPre = state.currentPage + d;
    if (targetPre >= 1 && targetPre <= state.totalPages) {
      const pre = new Image();
      pre.src = getPageImageUrl(targetPre);
    }
  }

  document.getElementById('btnPrevStage').disabled = state.currentPage <= 1;
  document.getElementById('btnNextStage').disabled = state.currentPage >= state.totalPages;
  setHashPage(state.currentPage);
  highlightActiveTOCAndThumb();
}

/**
 * GLITCH-FREE DIAGONAL PAPER FOLD & CYLINDRICAL CURL PHYSICS ENGINE
 * Replicates the 4-layer mask + curled flap geometry of physical textbooks
 */
async function animateRealisticFlip(targetPage, direction) {
  if (state.isFlipping) return;
  if (!state.isUnlocked) {
    checkPasswordProtectionGate();
    return;
  }

  state.isFlipping = true;

  // Ensure spread layout matches target mode if transitioning from single cover (page 1) to double spread
  const oldInfo = getSpreadPages(state.currentPage);
  const newInfo = getSpreadPages(targetPage);

  if (oldInfo.mode !== newInfo.mode && newInfo.mode === 'double') {
    const leftSlot = document.getElementById('leftPageSlot');
    const rightSlot = document.getElementById('rightPageSlot');
    const spread = document.getElementById('bookSpread');
    const spine = document.getElementById('spineShadow');
    const stage = document.getElementById('stageViewport');
    const availW = stage.clientWidth - 104;
    const availH = stage.clientHeight - 40;
    const ratio = state.config ? state.config.pageRatio || 1.4142 : 1.4142;
    let pageH = availH;
    let pageW = Math.floor(pageH / ratio);
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
    state.pageW = pageW;
    state.pageH = pageH;
    document.getElementById('leftPageImg').src = getPageImageUrl(1);
    document.getElementById('rightPageImg').src = getPageImageUrl(1);
  }

  const revealLayer = document.getElementById('flipRevealLayer');
  const revealImg = document.getElementById('revealImg');
  const revealShadow = document.getElementById('revealCreaseShadow');
  const flapWrap = document.getElementById('flipCurlFlapWrap');
  const flap = document.getElementById('flipCurlFlap');
  const flapImg = document.getElementById('flapImg');
  const rollShade = document.getElementById('flapRollShade');

  const w = state.pageW;
  const h = state.pageH;
  const isDouble = newInfo.mode === 'double' || oldInfo.mode === 'double';

  const incomingLeft = newInfo.mode === 'double' ? newInfo.left : newInfo.right;
  const incomingRight = newInfo.right;

  if (direction === 'next') {
    revealImg.src = getPageImageUrl(incomingRight);
    flapImg.src = getPageImageUrl(incomingLeft);
  } else {
    revealImg.src = getPageImageUrl(incomingLeft);
    flapImg.src = getPageImageUrl(incomingRight);
  }

  window.flipSound.playFlip();

  revealLayer.style.width = `${w}px`;
  revealLayer.style.height = `${h}px`;
  revealLayer.style.left = direction === 'next' && isDouble ? `${w}px` : '0px';

  flap.style.width = `${w}px`;
  flap.style.height = `${h}px`;
  flapWrap.style.filter =
    direction === 'next'
      ? 'drop-shadow(-16px 8px 22px rgba(0, 0, 0, 0.52))'
      : 'drop-shadow(16px 8px 22px rgba(0, 0, 0, 0.52))';

  revealLayer.classList.add('active');
  flapWrap.classList.add('active');

  const duration = 680;
  const startTime = performance.now();

  function easeCosine(t) {
    return 0.5 - 0.5 * Math.cos(t * Math.PI);
  }

  function stepFrame(now) {
    const rawT = Math.min(1, (now - startTime) / duration);
    const p = easeCosine(rawT);
    const sinArc = Math.sin(p * Math.PI);
    const slant = sinArc * (w * 0.14);

    if (direction === 'next') {
      const revealLocalX = w * (1 - p);
      const rTop = Math.max(0, Math.min(w, revealLocalX + slant));
      const rBot = Math.max(0, Math.min(w, revealLocalX - slant));
      revealLayer.style.clipPath = `polygon(${rTop.toFixed(1)}px 0px, ${w}px 0px, ${w}px ${h}px, ${rBot.toFixed(1)}px ${h}px)`;

      revealShadow.style.left = `${(revealLocalX - 6).toFixed(1)}px`;
      revealShadow.style.transform = `rotate(${(sinArc * 4.8).toFixed(2)}deg)`;
      revealShadow.style.opacity = (0.85 * sinArc).toFixed(2);

      const leadX = isDouble ? 2 * w * (1 - p) : w * (1 - p) - w * 0.42 * sinArc;
      const localFoldX = isDouble ? w * p : w * 0.42 * sinArc;
      const fTop = Math.max(0, Math.min(w, localFoldX + slant));
      const fBot = Math.max(0, Math.min(w, localFoldX - slant));
      const tiltDeg = sinArc * 4.8;

      flap.style.left = `${leadX.toFixed(1)}px`;
      flap.style.transformOrigin = `${localFoldX.toFixed(1)}px 50%`;
      flap.style.transform = `rotate(${tiltDeg.toFixed(2)}deg)`;
      flap.style.clipPath = `polygon(0px 0px, ${fTop.toFixed(1)}px 0px, ${fBot.toFixed(1)}px ${h}px, 0px ${h}px)`;

      rollShade.style.left = `${(localFoldX - 70).toFixed(1)}px`;
      rollShade.style.opacity = (0.35 + 0.65 * sinArc).toFixed(2);
    } else {
      const revealLocalX = w * p;
      const rTop = Math.max(0, Math.min(w, revealLocalX - slant));
      const rBot = Math.max(0, Math.min(w, revealLocalX + slant));
      revealLayer.style.clipPath = `polygon(0px 0px, ${rTop.toFixed(1)}px 0px, ${rBot.toFixed(1)}px ${h}px, 0px ${h}px)`;

      revealShadow.style.left = `${(revealLocalX - 75).toFixed(1)}px`;
      revealShadow.style.transform = `rotate(${(-sinArc * 4.8).toFixed(2)}deg) scaleX(-1)`;
      revealShadow.style.opacity = (0.85 * sinArc).toFixed(2);

      const leadX = isDouble ? 2 * w * p - w : w * p - w * (1 - 0.42 * sinArc);
      const localFoldX = isDouble ? w * (1 - p) : w * (1 - 0.42 * sinArc);
      const fTop = Math.max(0, Math.min(w, localFoldX - slant));
      const fBot = Math.max(0, Math.min(w, localFoldX + slant));
      const tiltDeg = -sinArc * 4.8;

      flap.style.left = `${leadX.toFixed(1)}px`;
      flap.style.transformOrigin = `${localFoldX.toFixed(1)}px 50%`;
      flap.style.transform = `rotate(${tiltDeg.toFixed(2)}deg)`;
      flap.style.clipPath = `polygon(${fTop.toFixed(1)}px 0px, ${w}px 0px, ${w}px ${h}px, ${fBot.toFixed(1)}px ${h}px)`;

      rollShade.style.left = `${localFoldX.toFixed(1)}px`;
      rollShade.style.transform = 'scaleX(-1)';
      rollShade.style.opacity = (0.35 + 0.65 * sinArc).toFixed(2);
    }

    if (rawT < 1) {
      requestAnimationFrame(stepFrame);
    } else {
      revealLayer.classList.remove('active');
      flapWrap.classList.remove('active');
      flap.style.transform = '';
      flap.style.clipPath = '';
      rollShade.style.transform = '';
      state.isFlipping = false;
      renderStaticSpread(targetPage);
    }
  }

  requestAnimationFrame(stepFrame);
}

function goToPage(targetPage, dir) {
  targetPage = Math.max(1, Math.min(state.totalPages, targetPage));
  if (targetPage === state.currentPage || state.isFlipping) return;
  const direction = dir || (targetPage > state.currentPage ? 'next' : 'prev');
  animateRealisticFlip(targetPage, direction);
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

  renderStaticSpread(state.currentPage);

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
      card.addEventListener('click', () => goToPage(pObj.page));
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
  window.addEventListener('resize', () => renderStaticSpread(state.currentPage));

  document.getElementById('btnPrevStage').addEventListener('click', stepPrev);
  document.getElementById('btnNextStage').addEventListener('click', stepNext);
  document.getElementById('btnFirstPage').addEventListener('click', () => goToPage(1, 'prev'));
  document.getElementById('btnPrevPage').addEventListener('click', stepPrev);
  document.getElementById('btnNextPage').addEventListener('click', stepNext);
  document.getElementById('btnLastPage').addEventListener('click', () => goToPage(state.totalPages, 'next'));

  document.getElementById('cornerLeft').addEventListener('click', stepPrev);
  document.getElementById('cornerRight').addEventListener('click', stepNext);

  document.getElementById('pageInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const val = parseInt(e.target.value, 10);
      if (!isNaN(val)) goToPage(val);
    }
  });

  window.addEventListener('keydown', (e) => {
    if (!state.isUnlocked) return;
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) return;
    if (e.key === 'ArrowRight') stepNext();
    else if (e.key === 'ArrowLeft') stepPrev();
    else if (e.key === '+' || e.key === '=') setZoom(state.zoom + 0.25);
    else if (e.key === '-') setZoom(state.zoom - 0.25);
    else if (e.key === '0') setZoom(1);
  });

  // Touch & Mouse Drag-to-Flip Gesture on Book Spread
  let dragPageStartX = null;
  const spreadEl = document.getElementById('bookSpread');

  spreadEl.addEventListener('pointerdown', (e) => {
    if (state.annoActive || state.zoom > 1.05 || !state.isUnlocked) return;
    dragPageStartX = e.clientX;
  });

  window.addEventListener('pointerup', (e) => {
    if (dragPageStartX === null) return;
    const dx = e.clientX - dragPageStartX;
    dragPageStartX = null;
    if (dx < -55) stepNext();
    else if (dx > 55) stepPrev();
  });

  // Mouse pan when zoomed
  const stage = document.getElementById('stageViewport');
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
    renderStaticSpread(state.currentPage);
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
    renderStaticSpread(state.currentPage);
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

  const tierSwitcher = document.getElementById('tierSwitcher');
  if (tierSwitcher) {
    tierSwitcher.addEventListener('change', (e) => {
      applyLicenseTier(e.target.value);
      showToast(`Simulasi Lisensi Diubah ke: ${e.target.value.toUpperCase()}`);
    });
  }

  // Password Gate Form
  const pwForm = document.getElementById('pwGateForm');
  if (pwForm) {
    pwForm.addEventListener('submit', (e) => {
      e.preventDefault();
      submitBookPassword(document.getElementById('pwGateInput').value);
    });
  }
  const btnBypass = document.getElementById('btnAdminBypassPw');
  if (btnBypass) {
    btnBypass.addEventListener('click', () => submitBookPassword('__ADMIN_BYPASS__'));
  }

  // Quick Password Configuration Modal (for Admin/Guru)
  const btnQuickPw = document.getElementById('btnQuickPassword');
  if (btnQuickPw) {
    btnQuickPw.addEventListener('click', () => {
      const isProtected = Boolean(state.config && state.config.security && state.config.security.isPasswordProtected);
      document.getElementById('cfgPwEnable').checked = isProtected;
      document.getElementById('quickPwModal').classList.add('open');
    });
  }
}

document.addEventListener('DOMContentLoaded', initViewer);
