let allBooks = [];
let activeCategory = 'ALL';
let activeTier = 'ALL';
let searchKeyword = '';
let currentUser = null;
let pendingUploadAfterAuth = false;
let currentCaptchaId = '';
let pendingVerifyEmail = '';

function formatRupiah(num) {
  return 'Rp ' + Number(num || 0).toLocaleString('id-ID');
}

function triggerUploadBook() {
  if (!currentUser) {
    pendingUploadAfterAuth = true;
    openAuthModal(
      'register',
      '🔒 Fitur Unggah Buku PDF hanya tersedia bagi pengguna yang sudah registrasi dan verifikasi email. Silakan daftar akun baru (atau masuk jika sudah punya akun) terlebih dahulu.'
    );
    return;
  }
  if (currentUser.name) {
    document.getElementById('upAuthor').value = currentUser.name;
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
  const adminBtn = document.getElementById('navAdminBtn');
  if (adminBtn) {
    if (currentUser) {
      adminBtn.style.display = 'inline-flex';
      if (currentUser.role === 'admin') {
        adminBtn.href = '/admin';
        adminBtn.innerHTML = '🛡️ Super Admin';
      } else {
        adminBtn.href = '/dashboard';
        adminBtn.innerHTML = '👤 User Panel';
      }
    } else {
      adminBtn.style.display = 'none';
    }
  }
  if (authBtn) {
    if (currentUser) {
      authBtn.innerHTML = `👤 ${currentUser.name.split(' ')[0]} <small style="opacity:0.75">(${currentUser.role.toUpperCase()})</small> • Keluar`;
      authBtn.onclick = () => {
        if (confirm(`Anda masuk sebagai ${currentUser.name} (${currentUser.email}). Ingin keluar (Logout)?`)) {
          logoutUser();
        }
      };
    } else {
      authBtn.innerHTML = 'Sign in';
      authBtn.onclick = () => {
        pendingUploadAfterAuth = false;
        openAuthModal('login');
      };
    }
  }
}

async function loadLoginCaptcha() {
  try {
    const res = await fetch('/api/auth/captcha');
    if (res.ok) {
      const data = await res.json();
      currentCaptchaId = data.captchaId;
      const qEl = document.getElementById('loginCaptchaQuestion');
      if (qEl) qEl.textContent = data.question;
      const ansEl = document.getElementById('loginCaptchaAnswer');
      if (ansEl) ansEl.value = '';
    }
  } catch (e) {
    console.error('Captcha error:', e);
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
  const loginForm = document.getElementById('loginForm');
  const regForm = document.getElementById('registerForm');
  const verifyForm = document.getElementById('verifyEmailForm');
  const tabsWrap = document.getElementById('authTabsWrap');

  if (tab === 'verify') {
    loginForm.style.display = 'none';
    regForm.style.display = 'none';
    verifyForm.style.display = 'block';
    tabsWrap.style.display = 'none';
    document.getElementById('authModalTitle').textContent = '📧 Verifikasi Alamat Email';
    return;
  }

  tabsWrap.style.display = 'grid';
  verifyForm.style.display = 'none';
  const isLogin = tab === 'login';
  loginForm.style.display = isLogin ? 'block' : 'none';
  regForm.style.display = isLogin ? 'none' : 'block';
  document.getElementById('tabBtnLogin').className = isLogin ? 'btn btn-primary' : 'btn';
  document.getElementById('tabBtnRegister').className = isLogin ? 'btn' : 'btn btn-primary';
  document.getElementById('authModalTitle').textContent = isLogin
    ? '👤 Masuk Akun FlipLabs'
    : '✨ Registrasi Pengguna Baru';

  if (isLogin) {
    loadLoginCaptcha();
  }
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
        captchaId: currentCaptchaId,
        captchaAnswer: document.getElementById('loginCaptchaAnswer').value,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      loadLoginCaptcha();
      const detail = data.detail || 'Gagal login';
      if (detail.startsWith('UNVERIFIED_EMAIL:')) {
        const parts = detail.split(':');
        pendingVerifyEmail = parts[1];
        document.getElementById('verifyTargetEmail').textContent = pendingVerifyEmail;
        switchAuthTab('verify');
        return;
      }
      throw new Error(detail);
    }

    localStorage.setItem('fliplabs_token', data.token);
    localStorage.setItem('fliplabs_user', JSON.stringify(data.user));
    loadAuthSession();
    document.getElementById('authModal').classList.remove('open');
    fetchBooks();
    if (pendingUploadAfterAuth) {
      pendingUploadAfterAuth = false;
      triggerUploadBook();
    }
  } catch (err) {
    statusEl.textContent = '❌ ' + err.message;
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const statusEl = document.getElementById('regStatus');
  const btn = document.getElementById('btnSubmitRegister');
  statusEl.textContent = '';
  btn.disabled = true;
  btn.textContent = '⏳ Mengirim Kode OTP ke Email Anda...';

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

    pendingVerifyEmail = data.email;
    document.getElementById('verifyTargetEmail').textContent = pendingVerifyEmail;
    document.getElementById('verifyStatus').style.color = '#0088ff';
    document.getElementById('verifyStatus').textContent = '✅ ' + (data.message || 'Kode OTP terkirim ke email Anda.');
    switchAuthTab('verify');
  } catch (err) {
    statusEl.textContent = '❌ ' + err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = '📧 Daftar & Kirim Kode Verifikasi Email';
  }
}

async function handleVerifyEmail(e) {
  e.preventDefault();
  const statusEl = document.getElementById('verifyStatus');
  statusEl.style.color = '#dc2626';
  statusEl.textContent = '';

  try {
    const res = await fetch('/api/auth/verify-email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: pendingVerifyEmail,
        otpCode: document.getElementById('verifyOtpInput').value,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Kode OTP salah');

    localStorage.setItem('fliplabs_token', data.token);
    localStorage.setItem('fliplabs_user', JSON.stringify(data.user));
    loadAuthSession();
    document.getElementById('authModal').classList.remove('open');
    fetchBooks();
    if (pendingUploadAfterAuth) {
      pendingUploadAfterAuth = false;
      triggerUploadBook();
    }
  } catch (err) {
    statusEl.textContent = '❌ ' + err.message;
  }
}

async function resendEmailOtp() {
  if (!pendingVerifyEmail) return;
  const statusEl = document.getElementById('verifyStatus');
  statusEl.style.color = '#0088ff';
  statusEl.textContent = '⏳ Mengirim ulang kode OTP...';
  try {
    const res = await fetch('/api/auth/resend-verification', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: pendingVerifyEmail }),
    });
    const data = await res.json();
    statusEl.textContent = '✅ ' + (data.message || 'Kode OTP baru telah dikirim.');
  } catch (e) {
    statusEl.style.color = '#dc2626';
    statusEl.textContent = '❌ Gagal mengirim ulang kode OTP.';
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
    const isPaid = Boolean(book.isForSale && book.price > 0);
    const priceBadgeHtml = isPaid
      ? `<span style="position:absolute;bottom:10px;right:10px;background:#0088ff;color:#fff;font-size:10.5px;font-weight:800;padding:3px 9px;border-radius:999px;z-index:6;box-shadow:0 2px 8px rgba(0,0,0,0.35);">🛒 ${formatRupiah(book.price)}</span>`
      : `<span style="position:absolute;bottom:10px;right:10px;background:#10b981;color:#fff;font-size:10px;font-weight:800;padding:3px 9px;border-radius:999px;z-index:6;">GRATIS</span>`;
    const lockBadgeHtml = isLocked
      ? `<span style="position:absolute;top:10px;left:10px;background:#fefce8;border:1px solid #eab308;color:#854d0e;font-size:10px;font-weight:800;padding:3px 7px;border-radius:999px;z-index:6;">🔒 Sandi</span>`
      : '';

    const item = document.createElement('div');
    item.className = 'book-item';
    item.innerHTML = `
      <div class="book-3d-wrap" onclick="window.location.href='/view/${book.id}#p=1'">
        <div class="book-3d-cover">
          ${lockBadgeHtml}
          <span class="tier-pill ${tier}">${tier}</span>
          ${priceBadgeHtml}
          <img src="/books/${book.id}/files/shot.jpg" onerror="this.src='/books/${book.id}/files/thumb/1.webp'" alt="${book.title}">
        </div>
      </div>
      <div class="book-meta">
        <h3 title="${book.title}">${book.title}</h3>
        <p>${book.author} • <b>${book.totalPageCount} Hal</b> • 👁 ${book.viewsCount || 1}</p>
        <div class="book-card-btns">
          <a href="/view/${book.id}#p=1" class="mini-btn read">${isPaid && !book.isOwned ? '📖 Preview' : '📖 Baca 3D'}</a>
          ${
            isPaid && !book.isOwned
              ? `<a href="/marketplace" class="mini-btn" style="border-color:#0088ff;color:#0088ff;">🛒 Beli</a>`
              : `<button class="mini-btn" onclick="openEmbedBook('${book.id}', '${book.title.replace(/'/g, "\\'")}')">🔗 Embed</button>`
          }
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
  formData.append('price', document.getElementById('upPrice').value || '0');
  formData.append('previewPages', document.getElementById('upPreviewPages').value || '3');

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

  const h = window.location.hash.toLowerCase();
  if (h === '#login') {
    openAuthModal('login');
  } else if (h === '#register') {
    openAuthModal('register');
  } else if (h === '#upload') {
    triggerUploadBook();
  } else if (h === '#verified') {
    openAuthModal('login', '✅ Alamat email Anda telah berhasil diverifikasi! Silakan masuk menggunakan akun Anda.');
  }

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
  document.getElementById('verifyEmailForm').addEventListener('submit', handleVerifyEmail);
});
