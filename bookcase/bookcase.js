let allBooks = [];
let myCollectionIds = new Set();
let activeCategory = 'ALL';
let activeMarketTab = 'all';
let searchKeyword = '';
let currentUser = null;
let currentCaptchaId = '';
let pendingVerifyEmail = '';
let pendingBuyBookIdAfterAuth = '';

function formatRupiah(num) {
  return 'Rp ' + Number(num || 0).toLocaleString('id-ID');
}

function getToken() {
  return localStorage.getItem('fliplabs_token') || '';
}

function loadAuthSession() {
  try {
    const raw = localStorage.getItem('fliplabs_user');
    currentUser = raw ? JSON.parse(raw) : null;
  } catch (e) {
    currentUser = null;
  }

  const authBtn = document.getElementById('navAuthBtn');
  const regBtn = document.getElementById('navRegisterBtn');
  const studentBtn = document.getElementById('navStudentPanelBtn');
  const guruBtn = document.getElementById('navGuruPanelBtn');
  const adminBtn = document.getElementById('navSuperAdminBtn');

  if (studentBtn) {
    studentBtn.style.display = currentUser ? 'inline-flex' : 'none';
  }
  if (guruBtn) {
    guruBtn.style.display =
      currentUser && ['guru', 'admin'].includes(currentUser.role) ? 'inline-flex' : 'none';
  }
  if (adminBtn) {
    adminBtn.style.display =
      currentUser && currentUser.role === 'admin' ? 'inline-flex' : 'none';
  }

  if (authBtn) {
    if (currentUser) {
      if (regBtn) regBtn.style.display = 'none';
      authBtn.innerHTML = `👤 ${currentUser.name.split(' ')[0]} <small style="opacity:0.75">(${currentUser.role.toUpperCase()})</small> • Keluar`;
      authBtn.onclick = () => {
        if (confirm(`Anda masuk sebagai ${currentUser.name} (${currentUser.email}). Ingin keluar (Logout)?`)) {
          logoutUser();
        }
      };
    } else {
      if (regBtn) regBtn.style.display = 'inline-flex';
      authBtn.innerHTML = 'Masuk (Login)';
      authBtn.onclick = () => openAuthModal('login');
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
      const aEl = document.getElementById('loginCaptchaAnswer');
      if (qEl) qEl.textContent = data.question;
      if (aEl) aEl.value = '';
    }
  } catch (e) {
    console.warn('Captcha fetch error', e);
  }
}

function openAuthModal(tab = 'login', noticeText = '') {
  const banner = document.getElementById('authNoticeBanner');
  if (banner) {
    if (noticeText) {
      banner.textContent = noticeText;
      banner.style.display = 'block';
    } else {
      banner.style.display = 'none';
    }
  }
  switchAuthTab(tab);
  document.getElementById('authModal').classList.add('open');
}

function closeAuthModal() {
  document.getElementById('authModal').classList.remove('open');
}

function switchAuthTab(tab) {
  const isLogin = tab === 'login';
  const isRegister = tab === 'register';
  const isVerify = tab === 'verify';

  const switchRow = document.getElementById('authTabSwitchRow');
  if (switchRow) switchRow.style.display = isVerify ? 'none' : 'flex';

  document.getElementById('loginForm').style.display = isLogin ? 'block' : 'none';
  document.getElementById('registerForm').style.display = isRegister ? 'block' : 'none';
  const vf = document.getElementById('verifyOtpForm');
  if (vf) vf.style.display = isVerify ? 'block' : 'none';

  document.getElementById('tabBtnLogin').className = isLogin ? 'btn btn-primary' : 'btn';
  document.getElementById('tabBtnRegister').className = isRegister ? 'btn btn-primary' : 'btn';

  if (isVerify) {
    document.getElementById('authModalTitle').textContent = '📧 Verifikasi Kode OTP Email';
  } else {
    document.getElementById('authModalTitle').textContent = isLogin
      ? '👤 Masuk Akun EBOOK LABS'
      : '🎓 Daftar Akun Siswa EBOOK LABS';
  }
  document.getElementById('loginErrorMsg').textContent = '';
  document.getElementById('regErrorMsg').textContent = '';
  if (isLogin) {
    loadLoginCaptcha();
  }
}

async function logoutUser() {
  const token = getToken();
  if (token) {
    await fetch('/api/auth/logout', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    }).catch(() => {});
  }
  localStorage.removeItem('fliplabs_token');
  localStorage.removeItem('fliplabs_user');
  currentUser = null;
  myCollectionIds.clear();
  loadAuthSession();
  await fetchBooks();
}

async function resendVerificationOtp() {
  if (!pendingVerifyEmail) return;
  const errEl = document.getElementById('verifyOtpErrorMsg');
  errEl.style.color = '#0088ff';
  errEl.textContent = '⏳ Mengirim ulang kode OTP ke ' + pendingVerifyEmail + '...';
  try {
    const res = await fetch('/api/auth/resend-verification', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: pendingVerifyEmail }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal mengirim ulang OTP');
    errEl.style.color = '#10b981';
    errEl.textContent = '✅ ' + data.message;
  } catch (err) {
    errEl.style.color = '#ef4444';
    errEl.textContent = '❌ ' + err.message;
  }
}

async function fetchBooks() {
  try {
    const token = getToken();
    const headers = token ? { Authorization: `Bearer ${token}` } : {};

    const [bkRes, colRes] = await Promise.all([
      fetch('/api/books', { headers }),
      token ? fetch('/api/marketplace/my-collection', { headers }) : Promise.resolve(null),
    ]);

    const data = await bkRes.json();
    allBooks = data.books || [];

    myCollectionIds.clear();
    if (colRes && colRes.ok) {
      const colData = await colRes.json();
      (colData.collection || []).forEach((b) => myCollectionIds.add(b.id));
      (colData.uploadedBooks || []).forEach((b) => myCollectionIds.add(b.id));
    }

    updateCollectionCounters();
    renderBooksGrid();
  } catch (err) {
    console.error('Failed loading books:', err);
  }
}

function updateCollectionCounters() {
  const cnt = myCollectionIds.size;
  const navCnt = document.getElementById('navCollectionCount');
  const tabCnt = document.getElementById('tabCollectionCount');
  if (navCnt) navCnt.textContent = cnt;
  if (tabCnt) tabCnt.textContent = cnt;
}

function setMarketTab(tabName) {
  activeMarketTab = tabName;
  document.querySelectorAll('.mkt-tab-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.mtab === tabName);
  });
  renderBooksGrid();
}

function renderBooksGrid() {
  const grid = document.getElementById('booksGrid');
  if (!grid) return;
  grid.innerHTML = '';

  const filtered = allBooks.filter((b) => {
    const isPaid = Boolean(b.isForSale && b.price > 0);
    const isMine = Boolean(b.isOwned || myCollectionIds.has(b.id));

    if (activeMarketTab === 'paid' && !isPaid) return false;
    if (activeMarketTab === 'free' && isPaid) return false;
    if (activeMarketTab === 'collection' && !isMine) return false;

    const matchCat =
      activeCategory === 'ALL' ||
      (b.category && b.category.toLowerCase().includes(activeCategory.toLowerCase()));
    const q = searchKeyword.toLowerCase();
    const matchSearch =
      !q ||
      (b.title && b.title.toLowerCase().includes(q)) ||
      (b.subject && b.subject.toLowerCase().includes(q)) ||
      (b.author && b.author.toLowerCase().includes(q));
    return matchCat && matchSearch;
  });

  if (filtered.length === 0) {
    grid.innerHTML = `
      <div style="grid-column:1/-1;text-align:center;padding:48px 20px;color:var(--text-muted);background:#fff;border-radius:16px;border:1px solid var(--border-subtle);">
        ${
          activeMarketTab === 'collection'
            ? '🎒 <strong>Koleksi Buku Anda masih kosong (0 buku).</strong><br><span style="font-size:13px;">Silakan pilih buku dari tab <b>Semua Katalog</b> untuk membeli buku atau menyimpan buku gratis ke koleksi Anda.</span>'
            : 'Tidak ada buku yang cocok dengan filter pencarian Anda.'
        }
      </div>
    `;
    return;
  }

  filtered.forEach((book) => {
    const isLocked = Boolean(
      book.isPasswordProtected || (book.security && book.security.isPasswordProtected)
    );
    const isPaid = Boolean(book.isForSale && book.price > 0);
    const isOwned = Boolean(book.isOwned || myCollectionIds.has(book.id));

    const lockRibbon = isLocked
      ? `<span style="position:absolute;bottom:10px;right:10px;background:rgba(15,23,42,0.88);border:1px solid #f59e0b;color:#facc15;font-size:10.5px;font-weight:800;padding:3px 8px;border-radius:99px;z-index:5;">🔒 SANDI</span>`
      : '';

    const pricePill = isPaid
      ? `<span class="price-pill paid">🛒 ${formatRupiah(book.price)}</span>`
      : `<span class="price-pill free">GRATIS</span>`;

    const ownedPill = isOwned
      ? `<span class="owned-pill">✓ MILIK SAYA</span>`
      : '';

    let actionButtons = '';
    if (isPaid && !isOwned) {
      actionButtons = `
        <a href="/view/${book.id}#p=1" class="btn" style="flex:1;justify-content:center;font-size:12.5px;">📖 Sampel (${book.previewPages || 3} Hal)</a>
        <button class="btn btn-primary" style="flex:1;justify-content:center;font-size:12.5px;" onclick="openBuyModal('${book.id}')">🛒 Beli Buku</button>
      `;
    } else if (!isPaid && !isOwned) {
      actionButtons = `
        <a href="/view/${book.id}#p=1" class="btn btn-primary" style="flex:1;justify-content:center;font-size:12.5px;">📖 Baca 3D</a>
        <button class="btn" style="flex:1;justify-content:center;font-size:12.5px;" onclick="collectFreeBook('${book.id}')">➕ Koleksi</button>
      `;
    } else {
      actionButtons = `
        <a href="/view/${book.id}#p=1" class="btn btn-primary" style="flex:1;justify-content:center;font-size:12.5px;">📖 Baca Full 3D (Milik Saya)</a>
      `;
    }

    const card = document.createElement('div');
    card.className = 'book-card-3d';
    card.innerHTML = `
      <div class="book-cover-wrap" style="position:relative;cursor:pointer;" onclick="window.location.href='/view/${book.id}#p=1'">
        ${ownedPill}
        ${pricePill}
        ${lockRibbon}
        <img src="/books/${book.id}/files/shot.jpg" alt="${book.title}" onerror="this.src='/books/${book.id}/files/thumb/1.webp'">
      </div>
      <div class="book-meta">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span class="badge-cat">${book.category || 'Buku Digital'}</span>
          <span style="font-size:11.5px;color:var(--text-dim);font-weight:700;">${book.totalPageCount} Hal</span>
        </div>
        <div class="book-title" title="${book.title}">${book.title}</div>
        <div class="book-author">${book.author || 'Tim Guru Labschool'}</div>
        <div class="book-footer" style="gap:8px;">
          ${actionButtons}
        </div>
      </div>
    `;
    grid.appendChild(card);
  });
}

function openBuyModal(bookId) {
  if (!currentUser || !getToken()) {
    pendingBuyBookIdAfterAuth = bookId;
    openAuthModal(
      'login',
      '🛒 Silakan Masuk (atau Daftar Akun Siswa baru) terlebih dahulu untuk membeli buku dan menyimpannya ke Koleksi Buku Anda.'
    );
    return;
  }

  const book = allBooks.find((x) => x.id === bookId);
  if (!book) return;

  document.getElementById('buyBookId').value = book.id;
  document.getElementById('buyBookSummary').innerHTML = `
    <div style="font-weight:800;font-size:15.5px;color:#0f172a;margin-bottom:4px;">${book.title}</div>
    <div style="font-size:12.5px;color:#475569;margin-bottom:10px;">Penulis: ${book.author} • ${book.totalPageCount} Halaman Full 3D</div>
    <div style="font-size:22px;font-weight:900;color:#0088ff;">${formatRupiah(book.price)}</div>
  `;
  document.getElementById('buyStatusMsg').textContent = '';
  document.getElementById('buyModal').classList.add('open');
}

function closeBuyModal() {
  document.getElementById('buyModal').classList.remove('open');
}

async function collectFreeBook(bookId) {
  if (!currentUser || !getToken()) {
    openAuthModal(
      'login',
      '📚 Silakan Masuk (atau Daftar Akun Siswa) terlebih dahulu untuk menyimpan buku ke dalam Koleksi Buku Saya.'
    );
    return;
  }

  try {
    const res = await fetch(`/api/marketplace/collect/${bookId}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal menyimpan buku');
    myCollectionIds.add(bookId);
    updateCollectionCounters();
    renderBooksGrid();
    alert('✅ ' + data.message);
  } catch (err) {
    alert('❌ ' + err.message);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadAuthSession();
  fetchBooks();

  if (window.location.hash === '#verified') {
    openAuthModal('login', '✅ Email Anda telah berhasil diverifikasi! Silakan masuk ke akun Siswa Anda.');
  }

  document.querySelectorAll('#categoryPills .pill').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#categoryPills .pill').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      activeCategory = btn.dataset.cat;
      renderBooksGrid();
    });
  });

  const searchIn = document.getElementById('bookSearchInput');
  if (searchIn) {
    searchIn.addEventListener('input', (e) => {
      searchKeyword = e.target.value.trim();
      renderBooksGrid();
    });
  }

  // Buy Book Form Submission
  const buyForm = document.getElementById('buyBookForm');
  if (buyForm) {
    buyForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const bookId = document.getElementById('buyBookId').value;
      const paymentMethod = document.getElementById('buyPaymentMethod').value;
      const msgEl = document.getElementById('buyStatusMsg');
      const btn = document.getElementById('btnConfirmBuy');
      btn.disabled = true;
      msgEl.textContent = '⏳ Memproses pembayaran & membuka kunci buku...';

      try {
        const res = await fetch(`/api/marketplace/buy/${bookId}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({ paymentMethod }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Pembelian gagal');

        myCollectionIds.add(bookId);
        updateCollectionCounters();
        await fetchBooks();
        msgEl.style.color = '#10b981';
        msgEl.textContent = '🎉 ' + data.message;
        setTimeout(() => {
          closeBuyModal();
          setMarketTab('collection');
        }, 1100);
      } catch (err) {
        msgEl.style.color = '#ef4444';
        msgEl.textContent = '❌ ' + err.message;
      } finally {
        btn.disabled = false;
      }
    });
  }

  // Login Form Submission
  const loginForm = document.getElementById('loginForm');
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const errEl = document.getElementById('loginErrorMsg');
      errEl.textContent = '';

      try {
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: document.getElementById('loginEmail').value.trim(),
            password: document.getElementById('loginPassword').value,
            captchaId: currentCaptchaId,
            captchaAnswer: document.getElementById('loginCaptchaAnswer').value.trim(),
          }),
        });
        const data = await res.json();
        if (!res.ok) {
          loadLoginCaptcha();
          const detail = data.detail || 'Gagal masuk';
          if (detail.startsWith('UNVERIFIED_EMAIL:')) {
            const parts = detail.split(':');
            pendingVerifyEmail = parts[1];
            document.getElementById('verifyEmailTarget').textContent = pendingVerifyEmail;
            switchAuthTab('verify');
            return;
          }
          throw new Error(detail);
        }

        localStorage.setItem('fliplabs_token', data.token);
        localStorage.setItem('fliplabs_user', JSON.stringify(data.user));
        loadAuthSession();
        closeAuthModal();
        await fetchBooks();

        if (pendingBuyBookIdAfterAuth) {
          const targetId = pendingBuyBookIdAfterAuth;
          pendingBuyBookIdAfterAuth = '';
          openBuyModal(targetId);
        }
      } catch (err) {
        errEl.textContent = '❌ ' + err.message;
      }
    });
  }

  // Student Registration Form Submission (Role fixed to 'siswa')
  const registerForm = document.getElementById('registerForm');
  if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const errEl = document.getElementById('regErrorMsg');
      const btn = document.getElementById('btnSubmitRegister');
      errEl.textContent = '';
      btn.disabled = true;
      btn.textContent = '⏳ Mengirim Kode OTP via admin@labschool.xyz...';

      try {
        const res = await fetch('/api/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: document.getElementById('regName').value.trim(),
            email: document.getElementById('regEmail').value.trim(),
            unit: document.getElementById('regUnit').value.trim(),
            role: 'siswa',
            password: document.getElementById('regPassword').value,
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Gagal mendaftar');

        pendingVerifyEmail = data.email;
        document.getElementById('verifyEmailTarget').textContent = pendingVerifyEmail;
        switchAuthTab('verify');
      } catch (err) {
        errEl.textContent = '❌ ' + err.message;
      } finally {
        btn.disabled = false;
        btn.textContent = '📧 Daftar Sebagai Siswa & Kirim OTP';
      }
    });
  }

  // OTP Verification Form Submission
  const verifyOtpForm = document.getElementById('verifyOtpForm');
  if (verifyOtpForm) {
    verifyOtpForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const errEl = document.getElementById('verifyOtpErrorMsg');
      errEl.style.color = '#ef4444';
      errEl.textContent = '';

      try {
        const res = await fetch('/api/auth/verify-email', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: pendingVerifyEmail,
            otpCode: document.getElementById('verifyOtpInput').value.trim(),
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Verifikasi OTP gagal');

        localStorage.setItem('fliplabs_token', data.token);
        localStorage.setItem('fliplabs_user', JSON.stringify(data.user));
        loadAuthSession();
        closeAuthModal();
        await fetchBooks();

        if (pendingBuyBookIdAfterAuth) {
          const targetId = pendingBuyBookIdAfterAuth;
          pendingBuyBookIdAfterAuth = '';
          openBuyModal(targetId);
        }
      } catch (err) {
        errEl.textContent = '❌ ' + err.message;
      }
    });
  }
});
