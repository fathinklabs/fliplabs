let allBooks = [];
let activeCategory = 'ALL';
let activeTier = 'ALL';
let searchKeyword = '';

async function fetchBooks() {
  try {
    const res = await fetch('/api/books');
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
    const item = document.createElement('div');
    item.className = 'book-item';
    item.innerHTML = `
      <div class="book-3d-wrap" onclick="window.location.href='/view/${book.id}#p=1'">
        <div class="book-3d-cover">
          <span class="tier-pill ${tier}">${tier}</span>
          <img src="/books/${book.id}/files/shot.jpg" onerror="this.src='/books/${book.id}/files/thumb/1.webp'" alt="${book.title}">
        </div>
      </div>
      <div class="book-meta">
        <h3 title="${book.title}">${book.title}</h3>
        <p>${book.author} • <b>${book.totalPageCount} Hal</b></p>
        <div class="book-card-btns">
          <a href="/view/${book.id}#p=1" class="mini-btn read">📖 Baca 3D</a>
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

  btn.disabled = true;
  btn.textContent = '⏳ Mengonversi PDF ke Multi-Tier WebP...';
  statusEl.textContent = 'Sedang mengekstrak halaman WebP, Daftar Isi (TOC), dan indeks pencarian...';

  try {
    const res = await fetch('/api/upload', {
      method: 'POST',
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
});
