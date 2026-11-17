let currentUser = null;
let booksList = [];
let usersList = [];
let gateCaptchaId = '';
let pendingVerifyEmail = '';

function formatRupiah(num) {
  return 'Rp ' + Number(num || 0).toLocaleString('id-ID');
}

function getToken() {
  return localStorage.getItem('fliplabs_token') || '';
}

function authHeaders() {
  const tok = getToken();
  return {
    'Content-Type': 'application/json',
    ...(tok ? { Authorization: `Bearer ${tok}` } : {}),
  };
}

async function loadGateCaptcha() {
  try {
    const res = await fetch('/api/auth/captcha');
    if (res.ok) {
      const data = await res.json();
      gateCaptchaId = data.captchaId;
      document.getElementById('gateCaptchaQuestion').textContent = data.question;
      document.getElementById('gateCaptchaAnswer').value = '';
    }
  } catch (e) {}
}

async function checkAuthState() {
  const tok = getToken();
  if (!tok) {
    showGate(true);
    loadGateCaptcha();
    return;
  }
  try {
    const res = await fetch('/api/auth/me', { headers: authHeaders() });
    if (!res.ok) throw new Error('Invalid session');
    const data = await res.json();
    currentUser = data.user;
    localStorage.setItem('fliplabs_user', JSON.stringify(currentUser));
    if (currentUser.role !== 'admin') {
      showGate(true);
      const msgEl = document.getElementById('gateAuthMsg');
      if (msgEl) {
        msgEl.textContent = '🔒 Akses Ditolak: Portal /admin hanya untuk Super Administrator. Mengalihkan ke User Panel (/dashboard)...';
      }
      setTimeout(() => {
        window.location.href = '/dashboard';
      }, 1200);
      return;
    }
    showGate(false);
    populateMyProfile();
    await loadDashboardData();
  } catch (e) {
    localStorage.removeItem('fliplabs_token');
    localStorage.removeItem('fliplabs_user');
    showGate(true);
    loadGateCaptcha();
  }
}

function showGate(locked) {
  document.getElementById('authGateSection').style.display = locked ? 'block' : 'none';
  document.getElementById('dashboardSection').style.display = locked ? 'none' : 'block';
  const userPill = document.getElementById('topUserSummary');
  const btnLogout = document.getElementById('btnTopLogout');
  if (!locked && currentUser) {
    userPill.textContent = `${currentUser.name} (${currentUser.role.toUpperCase()} • ${currentUser.license_tier.toUpperCase()})`;
    btnLogout.style.display = 'inline-flex';
    document.getElementById('tabBtnUsers').style.display = currentUser.role === 'admin' ? 'inline-block' : 'none';
  } else {
    userPill.textContent = 'Belum Masuk';
    btnLogout.style.display = 'none';
  }
}

async function submitGateLogin(e) {
  if (e && e.preventDefault) e.preventDefault();
  const msgEl = document.getElementById('gateAuthMsg');
  msgEl.textContent = '';

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: document.getElementById('gateLoginEmail').value,
        password: document.getElementById('gateLoginPassword').value,
        captchaId: gateCaptchaId,
        captchaAnswer: document.getElementById('gateCaptchaAnswer').value,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      loadGateCaptcha();
      const detail = data.detail || 'Gagal login';
      if (detail.startsWith('UNVERIFIED_EMAIL:')) {
        const parts = detail.split(':');
        pendingVerifyEmail = parts[1];
        document.getElementById('gateVerifyEmailLabel').textContent = pendingVerifyEmail;
        document.getElementById('gateRegWrap').style.display = 'none';
        document.getElementById('gateVerifyWrap').style.display = 'block';
        return;
      }
      throw new Error(detail);
    }
    localStorage.setItem('fliplabs_token', data.token);
    localStorage.setItem('fliplabs_user', JSON.stringify(data.user));
    if (data.user && data.user.role !== 'admin') {
      msgEl.textContent = '🔒 Akun ini bukan Super Admin. Mengalihkan ke User Panel (/dashboard)...';
      setTimeout(() => {
        window.location.href = '/dashboard';
      }, 1000);
      return;
    }
    await checkAuthState();
  } catch (err) {
    msgEl.textContent = '❌ ' + err.message;
  }
}

async function submitGateRegister(e) {
  e.preventDefault();
  const msgEl = document.getElementById('gateRegMsg');
  const btn = document.getElementById('btnGateRegSubmit');
  msgEl.textContent = '';
  btn.disabled = true;
  btn.textContent = '⏳ Mengirim Kode OTP Email...';

  try {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: document.getElementById('gateRegName').value,
        email: document.getElementById('gateRegEmail').value,
        role: document.getElementById('gateRegRole').value,
        unit: document.getElementById('gateRegUnit').value,
        password: document.getElementById('gateRegPassword').value,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal registrasi');
    pendingVerifyEmail = data.email;
    document.getElementById('gateVerifyEmailLabel').textContent = pendingVerifyEmail;
    document.getElementById('gateRegWrap').style.display = 'none';
    document.getElementById('gateVerifyWrap').style.display = 'block';
  } catch (err) {
    msgEl.textContent = '❌ ' + err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = '📧 Daftar & Kirim Kode OTP Email';
  }
}

async function submitGateVerifyOtp(e) {
  e.preventDefault();
  const msgEl = document.getElementById('gateVerifyMsg');
  msgEl.textContent = '';

  try {
    const res = await fetch('/api/auth/verify-email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: pendingVerifyEmail,
        otpCode: document.getElementById('gateVerifyOtp').value,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Kode OTP tidak sesuai');
    localStorage.setItem('fliplabs_token', data.token);
    localStorage.setItem('fliplabs_user', JSON.stringify(data.user));
    if (data.user && data.user.role !== 'admin') {
      msgEl.textContent = '🔒 Akun ini bukan Super Admin. Mengalihkan ke User Panel (/dashboard)...';
      setTimeout(() => {
        window.location.href = '/dashboard';
      }, 1000);
      return;
    }
    await checkAuthState();
  } catch (err) {
    msgEl.textContent = '❌ ' + err.message;
  }
}

async function logoutAdmin() {
  await fetch('/api/auth/logout', { method: 'POST', headers: authHeaders() }).catch(() => {});
  localStorage.removeItem('fliplabs_token');
  localStorage.removeItem('fliplabs_user');
  currentUser = null;
  showGate(true);
  loadGateCaptcha();
}

async function loadDashboardData() {
  try {
    const [ovRes, bkRes] = await Promise.all([
      fetch('/api/admin/overview', { headers: authHeaders() }),
      fetch('/api/books', { headers: authHeaders() }),
    ]);

    if (ovRes.ok) {
      const ov = await ovRes.json();
      document.getElementById('kpiTotalBooks').textContent = ov.totalBooks;
      document.getElementById('kpiTotalPages').textContent = `${ov.totalPagesRendered} Halaman WebP`;
      document.getElementById('kpiTotalViews').textContent = ov.totalBookViews;
      document.getElementById('kpiTotalUsers').textContent = ov.totalUsers;
      document.getElementById('kpiPlanSummary').textContent =
        `Enterprise: ${ov.planDistribution.enterprise} • Pro: ${ov.planDistribution.pro} • Basic: ${ov.planDistribution.basic}`;
      document.getElementById('kpiTotalRevenue').textContent = formatRupiah(ov.totalSalesRevenue || 0);
      document.getElementById('kpiSalesCount').textContent = `${ov.totalSalesCount || 0} Transaksi Terjual`;
    }

    if (bkRes.ok) {
      const bData = await bkRes.json();
      booksList = bData.books || [];
      renderBooksTable();
    }

    if (currentUser && currentUser.role === 'admin') {
      const uRes = await fetch('/api/admin/users', { headers: authHeaders() });
      if (uRes.ok) {
        const uData = await uRes.json();
        usersList = uData.users || [];
        renderUsersTable();
      }
    }
  } catch (err) {
    console.error('Failed loading dashboard data:', err);
  }
}

function renderBooksTable() {
  const tbody = document.getElementById('booksTableBody');
  tbody.innerHTML = '';

  const canEdit = currentUser && ['admin', 'guru'].includes(currentUser.role);

  booksList.forEach((b) => {
    const tier = (b.licenseTier || 'enterprise').toLowerCase();
    const isLocked = Boolean(b.isPasswordProtected || (b.security && b.security.isPasswordProtected));
    const isPaid = Boolean(b.isForSale && b.price > 0);
    const pwBadge = isLocked
      ? `<span class="badge" style="background:#fefce8;color:#854d0e;border:1px solid #eab308;">🔒 Terkunci Sandi</span>`
      : `<span class="badge" style="background:#ecfdf5;color:#047857;">🔓 Publik</span>`;
    const priceBadge = isPaid
      ? `<span class="badge" style="background:#eff6ff;color:#0088ff;border:1px solid #bfdbfe;">🛒 ${formatRupiah(b.price)}</span><br><small style="color:var(--text-dim);">Preview: ${b.previewPages} Hal</small>`
      : `<span class="badge" style="background:#f1f5f9;color:#475569;">Gratis</span>`;

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>
        <div style="display:flex;align-items:center;gap:12px;">
          <img src="/books/${b.id}/files/shot.jpg" onerror="this.src='/books/${b.id}/files/thumb/1.webp'" style="width:38px;height:52px;object-fit:cover;border-radius:4px;border:1px solid #e2e8f0;">
          <div>
            <div style="font-weight:800;color:#0f172a;">${b.title}</div>
            <div style="font-size:11.5px;color:var(--text-dim);">${b.author} • 👁 ${b.viewsCount || 1} views</div>
          </div>
        </div>
      </td>
      <td>${b.category || '-'}<br><small style="color:var(--text-dim)">${b.subject || ''}</small></td>
      <td><b>${b.totalPageCount}</b> Hal</td>
      <td>${priceBadge}</td>
      <td><span class="badge ${tier}">${tier}</span></td>
      <td>${pwBadge}</td>
      <td>
        <div style="display:flex;gap:6px;flex-wrap:wrap;">
          <a href="/view/${b.id}#p=1" class="btn" style="padding:5px 10px;font-size:11.5px;">📖 Buka</a>
          ${
            canEdit
              ? `<button class="btn" style="padding:5px 10px;font-size:11.5px;" onclick="openEditBookModal('${b.id}')">✏️ Edit & Harga</button>`
              : ''
          }
          ${
            currentUser && currentUser.role === 'admin'
              ? `<button class="btn btn-danger" style="padding:5px 10px;font-size:11.5px;" onclick="deleteBook('${b.id}', '${b.title.replace(/'/g, "\\'")}')">🗑</button>`
              : ''
          }
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function openEditBookModal(bookId) {
  const b = booksList.find((x) => x.id === bookId);
  if (!b) return;
  const isLocked = Boolean(b.isPasswordProtected || (b.security && b.security.isPasswordProtected));
  const currentPw = (b.security && b.security.password) || '';

  document.getElementById('ebId').value = b.id;
  document.getElementById('ebTitle').value = b.title;
  document.getElementById('ebAuthor').value = b.author || '';
  document.getElementById('ebCategory').value = b.category || '';
  document.getElementById('ebSubject').value = b.subject || '';
  document.getElementById('ebTier').value = (b.licenseTier || 'enterprise').toLowerCase();
  document.getElementById('ebIsForSale').checked = Boolean(b.isForSale && b.price > 0);
  document.getElementById('ebPrice').value = b.price || 0;
  document.getElementById('ebPreviewPages').value = b.previewPages || 3;
  document.getElementById('ebPwProtected').checked = isLocked;
  document.getElementById('ebPassword').value = currentPw;
  document.getElementById('editBookModal').classList.add('open');
}

async function submitEditBook(e) {
  e.preventDefault();
  const bookId = document.getElementById('ebId').value;
  const isProtected = document.getElementById('ebPwProtected').checked;
  const pwVal = document.getElementById('ebPassword').value.trim();
  const isForSale = document.getElementById('ebIsForSale').checked;
  const priceVal = parseInt(document.getElementById('ebPrice').value || '0', 10);
  const previewVal = parseInt(document.getElementById('ebPreviewPages').value || '3', 10);

  if (isProtected && !pwVal) {
    alert('Masukkan kata sandi buku jika proteksi kata sandi diaktifkan!');
    return;
  }

  try {
    const res = await fetch(`/api/admin/books/${bookId}`, {
      method: 'PUT',
      headers: authHeaders(),
      body: JSON.stringify({
        title: document.getElementById('ebTitle').value,
        author: document.getElementById('ebAuthor').value,
        category: document.getElementById('ebCategory').value,
        subject: document.getElementById('ebSubject').value,
        licenseTier: document.getElementById('ebTier').value,
        visibility: 'public',
        isPasswordProtected: isProtected,
        bookPassword: pwVal,
        isForSale: isForSale,
        price: isForSale ? priceVal : 0,
        previewPages: previewVal,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal menyimpan perubahan buku');
    document.getElementById('editBookModal').classList.remove('open');
    await loadDashboardData();
  } catch (err) {
    alert('❌ ' + err.message);
  }
}

async function deleteBook(bookId, title) {
  if (!confirm(`Yakin ingin menghapus buku "${title}" secara permanen?`)) return;
  try {
    const res = await fetch(`/api/admin/books/${bookId}`, {
      method: 'DELETE',
      headers: authHeaders(),
    });
    if (!res.ok) {
      const d = await res.json();
      throw new Error(d.detail || 'Gagal menghapus buku');
    }
    await loadDashboardData();
  } catch (err) {
    alert('❌ ' + err.message);
  }
}

function renderUsersTable() {
  const tbody = document.getElementById('usersTableBody');
  tbody.innerHTML = '';

  usersList.forEach((u) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>
        <div style="font-weight:800;color:#0f172a;">${u.name}</div>
        <div style="font-size:11.5px;color:var(--text-dim);">${u.email} ${u.email_verified ? '✅' : '⏳ Belum Verifikasi'}</div>
      </td>
      <td>${u.unit}</td>
      <td><span class="badge ${u.role}">${u.role}</span></td>
      <td><span class="badge ${u.license_tier}">${u.license_tier}</span></td>
      <td>
        <span class="badge" style="background:${u.status === 'active' ? '#ecfdf5' : '#fef2f2'};color:${u.status === 'active' ? '#047857' : '#dc2626'};">
          ${u.status}
        </span>
      </td>
      <td>
        <div style="display:flex;gap:6px;">
          <button class="btn" style="padding:5px 10px;font-size:11.5px;" onclick="openEditUserModal(${u.id})">✏️ Kelola</button>
          ${
            u.id !== currentUser.id
              ? `<button class="btn btn-danger" style="padding:5px 10px;font-size:11.5px;" onclick="deleteUser(${u.id}, '${u.email}')">🗑</button>`
              : ''
          }
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function openCreateUserModal() {
  document.getElementById('cuForm').reset();
  document.getElementById('createUserModal').classList.add('open');
}

async function submitCreateUser(e) {
  e.preventDefault();
  try {
    const res = await fetch('/api/admin/users', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        name: document.getElementById('cuName').value,
        email: document.getElementById('cuEmail').value,
        password: document.getElementById('cuPassword').value,
        role: document.getElementById('cuRole').value,
        license_tier: document.getElementById('cuTier').value,
        unit: document.getElementById('cuUnit').value,
        status: 'active',
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal membuat user');
    document.getElementById('createUserModal').classList.remove('open');
    await loadDashboardData();
  } catch (err) {
    alert('❌ ' + err.message);
  }
}

function openEditUserModal(userId) {
  const u = usersList.find((x) => x.id === userId);
  if (!u) return;
  document.getElementById('euId').value = u.id;
  document.getElementById('euName').value = u.name;
  document.getElementById('euEmail').value = u.email;
  document.getElementById('euUnit').value = u.unit || '';
  document.getElementById('euRole').value = u.role;
  document.getElementById('euTier').value = u.license_tier;
  document.getElementById('euStatus').value = u.status;
  document.getElementById('euPassword').value = '';
  document.getElementById('editUserModal').classList.add('open');
}

async function submitEditUser(e) {
  e.preventDefault();
  const uid = parseInt(document.getElementById('euId').value, 10);
  const newPw = document.getElementById('euPassword').value.trim();

  try {
    const res = await fetch(`/api/admin/users/${uid}`, {
      method: 'PUT',
      headers: authHeaders(),
      body: JSON.stringify({
        name: document.getElementById('euName').value,
        unit: document.getElementById('euUnit').value,
        role: document.getElementById('euRole').value,
        license_tier: document.getElementById('euTier').value,
        status: document.getElementById('euStatus').value,
        new_password: newPw || null,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal memperbarui user');
    document.getElementById('editUserModal').classList.remove('open');
    await loadDashboardData();
  } catch (err) {
    alert('❌ ' + err.message);
  }
}

async function deleteUser(uid, email) {
  if (!confirm(`Yakin ingin menghapus akun pengguna "${email}"?`)) return;
  try {
    const res = await fetch(`/api/admin/users/${uid}`, {
      method: 'DELETE',
      headers: authHeaders(),
    });
    if (!res.ok) {
      const d = await res.json();
      throw new Error(d.detail || 'Gagal menghapus pengguna');
    }
    await loadDashboardData();
  } catch (err) {
    alert('❌ ' + err.message);
  }
}

function populateMyProfile() {
  if (!currentUser) return;
  document.getElementById('myName').value = currentUser.name;
  document.getElementById('myEmail').value = currentUser.email;
  document.getElementById('myUnit').value = currentUser.unit || '';
  document.getElementById('myRoleBadge').textContent = currentUser.role.toUpperCase();
  document.getElementById('myTierBadge').textContent = currentUser.license_tier.toUpperCase();
}

async function submitMyProfile(e) {
  e.preventDefault();
  const msg = document.getElementById('myProfileMsg');
  msg.textContent = '';

  try {
    const res = await fetch('/api/auth/profile', {
      method: 'PUT',
      headers: authHeaders(),
      body: JSON.stringify({
        name: document.getElementById('myName').value,
        unit: document.getElementById('myUnit').value,
        new_password: document.getElementById('myNewPassword').value || null,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal menyimpan profil');
    document.getElementById('myNewPassword').value = '';
    msg.textContent = '✅ Profil dan pengaturan akun berhasil diperbarui!';
    await checkAuthState();
  } catch (err) {
    msg.textContent = '❌ ' + err.message;
  }
}

function switchDashTab(tabName) {
  ['books', 'users', 'profile'].forEach((t) => {
    const panel = document.getElementById(`panel-${t}`);
    if (panel) panel.style.display = t === tabName ? 'block' : 'none';
  });
  document.querySelectorAll('.tab-btn').forEach((b) => {
    b.classList.toggle('active', b.dataset.tab === tabName);
  });
}

document.addEventListener('DOMContentLoaded', () => {
  checkAuthState();
  const glf = document.getElementById('gateLoginForm');
  if (glf) glf.addEventListener('submit', submitGateLogin);
  const grf = document.getElementById('gateRegForm');
  if (grf) grf.addEventListener('submit', submitGateRegister);
  const gvf = document.getElementById('gateVerifyForm');
  if (gvf) gvf.addEventListener('submit', submitGateVerifyOtp);
  document.getElementById('editBookForm').addEventListener('submit', submitEditBook);
  document.getElementById('cuForm').addEventListener('submit', submitCreateUser);
  document.getElementById('euForm').addEventListener('submit', submitEditUser);
  document.getElementById('myProfileForm').addEventListener('submit', submitMyProfile);
});
