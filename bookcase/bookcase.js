let allBooks = [];
let activeCategory = 'ALL';
let activeTier = 'ALL';
let searchKeyword = '';
let currentUser = null;
let pendingUploadAfterAuth = false;

function triggerUploadBook() {
  if (!currentUser) {
    pendingUploadAfterAuth = true;
    openAuthModal(
      'register',
      '🔒 Fitur Unggah Buku PDF hanya tersedia bagi pengguna yang sudah registrasi akun. Silakan daftar akun baru (atau masuk jika sudah punya akun) terlebih dahulu.'
    );
    return;
  }
  document.getElementById('uploadModal').classList.add('open');
}

function loadAuthSession() {
  try {
    const raw = localStorage.getItem('fliplabs_user');
    currentUser = raw ? JSON.parse(raw) : null;
  } catch (e) {
    currentUser = null;
  }
  const authBtn = document.getElementById('navAuthBtn');
  if (authBtn) {
    if (currentUser) {
      authBtn.innerHTML = `👤 ${currentUser.name.split(' ')[0]} <small style="opacity:0.75">(${currentUser.role.toUpperCase()})</small>`;
      authBtn.onclick = () => {
        if (confirm(`Anda masuk sebagai ${currentUser.name} (${currentUser.email}). Ingin keluar (Logout)?`)) {
          logoutUser();
        }
      };
    } else {
      authBtn.innerHTML = '👤 Masuk / Daftar';
      authBtn.onclick = () => {
        pendingUploadAfterAuth = false;
        openAuthModal('login');
      };
    }
  }
}

function openAuthModal(tab, requirementNotice) {
  const banner = document.getElementById('authRequirementBanner');
  if (banner) {
    if (requirementNotice) {
      banner.textContent = requirementNotice;
      banner.style.display = 'block';
    } else {
      banner.style.display = 'none';
    }
  }
  switchAuthTab(tab || 'login');
  document.getElementById('authModal').classList.add('open');
}

function switchAuthTab(tab) {
  const isLogin = tab === 'login';
  document.getElementById('loginForm').style.display = isLogin ? 'block' : 'none';
  document.getElementById('registerForm').style.display = isLogin ? 'none' : 'block';
  document.getElementById('tabBtnLogin').className = isLogin ? 'btn btn-primary' : 'btn';
  document.getElementById('tabBtnRegister').className = isLogin ? 'btn' : 'btn btn-primary';
  document.getElementById('authModalTitle').textContent = isLogin
    ? '👤 Masuk Akun FlipLabs'
    : '✨ Registrasi Pengguna Baru';
}

async function handleLogin(e) {
  e.preventDefault();
  const statusEl = document.getElementById('loginStatus');
  statusEl.textContent = '';

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: document.getElementById('loginEmail').value,
        password: document.getElementById('loginPassword').value,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal login');

    localStorage.setItem('fliplabs_token', data.token);
    localStorage.setItem('fliplabs_user', JSON.stringify(data.user));
    loadAuthSession();
    document.getElementById('authModal').classList.remove('open');
    fetchBooks();
    if (pendingUploadAfterAuth) {
      pendingUploadAfterAuth = false;
      document.getElementById('uploadModal').classList.add('open');
    }
  } catch (err) {
    statusEl.textContent = '❌ ' + err.message;
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const statusEl = document.getElementById('regStatus');
  statusEl.textContent = '';

  try {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: document.getElementById('regName').value,
        email: document.getElementById('regEmail').value,
        role: document.getElementById('regRole').value,
        unit: document.getElementById('regUnit').value,
        password: document.getElementById('regPassword').value,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal mendaftar');

    localStorage.setItem('fliplabs_token', data.token);
    localStorage.setItem('fliplabs_user', JSON.stringify(data.user));
    loadAuthSession();
    document.getElementById('authModal').classList.remove('open');
    fetchBooks();
    if (pendingUploadAfterAuth) {
      pendingUploadAfterAuth = false;
      document.getElementById('uploadModal').classList.add('open');
    }
  } catch (err) {
    statusEl.textContent = '❌ ' + err.message;
  }
}

async function logoutUser() {
  const token = localStorage.getItem('fliplabs_token');
  if (token) {
    await fetch('/api/auth/logout', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    }).catch(() => {});
  }
  localStorage.removeItem('fliplabs_token');
  localStorage.removeItem('fliplabs_user');
  loadAuthSession();
}

async function fetchBooks() {
  try {
    const token = localStorage.getItem('fliplabs_token') || '';
    const res = await fetch('/api/books', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (res.ok) {
      const data = await res.json();
      allBooks = data.books || [];
      renderBookshelf();
    }
  } catch (err) {
    console.error('Error loading books:', err);
  }
}

function renderBookshelf() {
  const shelf = document.getElementById('shelfGrid');
  shelf.innerHTML = '';

  const filtered = allBooks.filter((b) => {
    const matchCat = activeCategory === 'ALL' || (b.category || '').toLowerCase() === activeCategory.toLowerCase();
    const matchTier = activeTier === 'ALL' || (b.licenseTier || '').toLowerCase() === activeTier.toLowerCase();
    const q = searchKeyword.toLowerCase();
    const matchSearch =
      !q ||
      (b.title || '').toLowerCase().includes(q) ||
      (b.author || '').toLowerCase().includes(q) ||
      (b.subject || '').toLowerCase().includes(q);
    return matchCat && matchTier && matchSearch;
  });

  if (!filtered.length) {
    shelf.innerHTML = `
      <div style="grid-column: 1 / -1; text-align:center; padding: 36px; color: var(--text-dim);">
        Tidak ada buku yang cocok dengan filter pencarian.
      </div>
    `;
    return;
  }

  filtered.forEach((book) => {
    const tier = (book.licenseTier || 'enterprise').toLowerCase();
    const isLocked = Boolean(book.isPasswordProtected || (book.security && book.security.isPasswordProtected));
    const lockBadgeHtml = isLocked
      ? `<span style="position:absolute;top:10px;left:10px;background:rgba(15,23,42,0.88);border:1px solid #eab308;color:#fde047;font-size:10px;font-weight:700;padding:3px 7px;border-radius:999px;z-index:6;">🔒 Sandi</span>`
      : '';

    const item = document.createElement('div');
    item.className = 'book-item';
    item.innerHTML = `
      <div class="book-3d-wrap" onclick="window.location.href='/view/${book.id}#p=1'">
        <div class="book-3d-cover">
          ${lockBadgeHtml}
          <span class="tier-pill ${tier}">${tier}</span>
          <img src="/books/${book.id}/files/shot.jpg" onerror="this.src='/books/${book.id}/files/thumb/1.webp'" alt="${book.title}">
        </div>
      </div>
      <div class="book-meta">
        <h3 title="${book.title}">${book.title}</h3>
        <p>${book.author} • <b>${book.totalPageCount} Hal</b> • 👁 ${book.viewsCount || 1}</p>
        <div class="book-card-btns">
          <a href="/view/${book.id}#p=1" class="mini-btn read">${isLocked ? '🔒 Buka' : '📖 Baca 3D'}</a>
          <button class="mini-btn" onclick="openEmbedBook('${book.id}', '${book.title.replace(/'/g, "\\'")}')">🔗 Embed</button>
        </div>
      </div>
    `;
    shelf.appendChild(item);
  });
}

function openEmbedBook(bookId, title) {
  const url = `${window.location.origin}/view/${bookId}#p=1`;
  document.getElementById('embedModalTitle').textContent = `Sematkan Buku: ${title}`;
  document.getElementById('embedDirectUrl').value = url;
  document.getElementById('embedIframeCode').value = `<iframe src="${url}" width="100%" height="650" frameborder="0" allowfullscreen></iframe>`;
  document.getElementById('embedModal').classList.add('open');
}

function openEmbedShelf() {
  const url = `${window.location.origin}/`;
  document.getElementById('embedModalTitle').textContent = 'Sematkan Rak Buku Digital (Virtual Bookcase)';
  document.getElementById('embedDirectUrl').value = url;
  document.getElementById('embedIframeCode').value = `<iframe src="${url}" width="100%" height="720" frameborder="0" allowfullscreen></iframe>`;
  document.getElementById('embedModal').classList.add('open');
}

async function handleUploadSubmit(e) {
  e.preventDefault();
  const btn = document.getElementById('btnSubmitUpload');
  const statusEl = document.getElementById('uploadStatus');
  const fileInput = document.getElementById('pdfFile');

  if (!fileInput.files.length) return;

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  formData.append('title', document.getElementById('upTitle').value);
  formData.append('author', document.getElementById('upAuthor').value);
  formData.append('category', document.getElementById('upCategory').value);
  formData.append('subject', document.getElementById('upSubject').value);
  formData.append('licenseTier', document.getElementById('upTier').value);
  formData.append('bookPassword', document.getElementById('upPassword').value || '');

  btn.disabled = true;
  btn.textContent = '⏳ Mengonversi PDF ke Multi-Tier WebP...';
  statusEl.textContent = 'Sedang mengekstrak halaman WebP, Daftar Isi (TOC), dan indeks pencarian...';

  const token = localStorage.getItem('fliplabs_token') || '';

  try {
    const res = await fetch('/api/upload', {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal mengonversi PDF');

    statusEl.textContent = `✅ Berhasil! Buku "${data.book.title}" (${data.book.totalPageCount} halaman) selesai dikonversi dalam ${data.book.conversionSeconds} detik.`;
    await fetchBooks();
    setTimeout(() => {
      document.getElementById('uploadModal').classList.remove('open');
      window.location.href = `/view/${data.book.id}#p=1`;
    }, 900);
  } catch (err) {
    statusEl.textContent = '❌ Error: ' + err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = '🚀 Proses & Terbitkan Flipbook';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadAuthSession();
  fetchBooks();

  document.querySelectorAll('.pill[data-cat]').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.pill[data-cat]').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      activeCategory = btn.dataset.cat;
      renderBookshelf();
    });
  });

  document.querySelectorAll('.pill[data-tier]').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.pill[data-tier]').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      activeTier = btn.dataset.tier;
      renderBookshelf();
    });
  });

  document.getElementById('shelfSearch').addEventListener('input', (e) => {
    searchKeyword = e.target.value;
    renderBookshelf();
  });

  document.getElementById('uploadForm').addEventListener('submit', handleUploadSubmit);
  document.getElementById('loginForm').addEventListener('submit', handleLogin);
  document.getElementById('registerForm').addEventListener('submit', handleRegister);
});
