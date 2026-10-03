// Popup logic for Screenshot Bookmark Extension

let activeTab = null;
let currentBookmark = null;
let apiBase = 'http://localhost:8000';
let searchDebounceTimer = null;
let activeTagFilter = null;

// DOM Elements
const serverBadge = document.getElementById('serverBadge');
const serverText = document.getElementById('serverText');
const settingsToggleBtn = document.getElementById('settingsToggleBtn');
const settingsPanel = document.getElementById('settingsPanel');
const closeSettingsBtn = document.getElementById('closeSettingsBtn');
const apiBaseInput = document.getElementById('apiBaseInput');
const saveSettingsBtn = document.getElementById('saveSettingsBtn');
const openWebUiLink = document.getElementById('openWebUiLink');

const statusBanner = document.getElementById('statusBanner');

const currentFavicon = document.getElementById('currentFavicon');
const currentTitle = document.getElementById('currentTitle');
const currentUrl = document.getElementById('currentUrl');
const bookmarkedBadge = document.getElementById('bookmarkedBadge');

const quickBookmarkBtn = document.getElementById('quickBookmarkBtn');
const captureTabBtn = document.getElementById('captureTabBtn');
const captureAreaBtn = document.getElementById('captureAreaBtn');

const tagsInput = document.getElementById('tagsInput');
const notesInput = document.getElementById('notesInput');

const searchInput = document.getElementById('searchInput');
const clearSearchBtn = document.getElementById('clearSearchBtn');
const tagPillsContainer = document.getElementById('tagPillsContainer');

const sectionTitle = document.getElementById('sectionTitle');
const bookmarkCount = document.getElementById('bookmarkCount');
const bookmarksList = document.getElementById('bookmarksList');

// Initialize popup
document.addEventListener('DOMContentLoaded', async () => {
  await initConfig();
  await loadActiveTab();
  await checkServerHealth();
  await loadRecentBookmarks();
  setupEventListeners();
});

async function initConfig() {
  const config = await chrome.runtime.sendMessage({ action: 'get-config' });
  if (config && config.apiBase) {
    apiBase = config.apiBase;
  }
  apiBaseInput.value = apiBase;
  openWebUiLink.href = apiBase;
}

async function loadActiveTab() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) return;
    activeTab = tab;

    currentTitle.textContent = tab.title || 'Untitled Tab';
    currentTitle.title = tab.title || '';

    try {
      const parsedUrl = new URL(tab.url);
      currentUrl.textContent = parsedUrl.hostname + parsedUrl.pathname;
    } catch (e) {
      currentUrl.textContent = tab.url || '';
    }
    currentUrl.title = tab.url || '';

    if (tab.favIconUrl) {
      currentFavicon.src = tab.favIconUrl;
    }

    // Try to get page metadata (selected text or meta description) from content script
    try {
      const response = await chrome.tabs.sendMessage(tab.id, { action: 'get-page-metadata' });
      if (response && response.metadata) {
        if (response.metadata.selectedText) {
          notesInput.value = response.metadata.selectedText;
        } else if (response.metadata.description) {
          notesInput.value = response.metadata.description;
        }
      }
    } catch (e) {
      // Content script might not be injected on special pages (chrome://, etc.)
    }

    // Check if current tab is already bookmarked
    if (tab.url && !tab.url.startsWith('chrome://')) {
      const checkResult = await chrome.runtime.sendMessage({ action: 'check-url', url: tab.url });
      if (checkResult && checkResult.bookmarked && checkResult.bookmark) {
        currentBookmark = checkResult.bookmark;
        bookmarkedBadge.classList.remove('hidden');
        quickBookmarkBtn.querySelector('.btn-label').textContent = 'Update';
        quickBookmarkBtn.querySelector('.btn-icon').textContent = '★';

        if (currentBookmark.tags && !tagsInput.value) {
          tagsInput.value = currentBookmark.tags;
        }
        if (currentBookmark.description && !notesInput.value) {
          notesInput.value = currentBookmark.description;
        }
      }
    }
  } catch (err) {
    console.warn('Could not inspect active tab:', err);
  }
}

async function checkServerHealth() {
  try {
    const res = await fetch(`${apiBase}/health`, { signal: AbortSignal.timeout(3000) });
    if (res.ok) {
      const data = await res.json();
      serverBadge.className = 'server-badge online';
      serverText.textContent = data.ocr_available ? 'Online (OCR)' : 'Online';
      serverBadge.title = `Server Connected: ${apiBase}`;
      return true;
    }
    throw new Error('Not OK');
  } catch (e) {
    serverBadge.className = 'server-badge offline';
    serverText.textContent = 'Offline';
    serverBadge.title = `Cannot connect to ${apiBase}. Ensure server is running.`;
    return false;
  }
}

async function loadRecentBookmarks() {
  bookmarksList.innerHTML = '<div class="loading-state">Loading bookmarks...</div>';
  try {
    const response = await chrome.runtime.sendMessage({ action: 'get-recent', limit: 20 });
    if (response && response.success) {
      renderBookmarks(response.bookmarks);
      extractAndRenderTags(response.bookmarks);
    } else {
      bookmarksList.innerHTML = '<div class="empty-state">Could not load bookmarks. Ensure server is running.</div>';
    }
  } catch (err) {
    bookmarksList.innerHTML = '<div class="empty-state">Server offline. Start backend server with: screenshot-bookmark-server</div>';
  }
}

function renderBookmarks(bookmarks) {
  bookmarkCount.textContent = bookmarks ? bookmarks.length : 0;
  if (!bookmarks || bookmarks.length === 0) {
    bookmarksList.innerHTML = '<div class="empty-state">No bookmarks saved yet. Save your first one above!</div>';
    return;
  }

  bookmarksList.innerHTML = bookmarks.map(b => {
    let domain = '';
    try {
      if (b.url) domain = new URL(b.url).hostname.replace('www.', '');
    } catch (e) {
      domain = b.url || '';
    }

    const tags = (b.tags || '').split(',').map(t => t.trim()).filter(Boolean);
    const fullImageUrl = b.image_url ? (b.image_url.startsWith('http') ? b.image_url : `${apiBase}${b.image_url}`) : null;

    return `
      <div class="bookmark-card" data-id="${b.id}">
        <div class="bookmark-thumb-wrap" title="${fullImageUrl ? 'Click to view full screenshot' : 'No screenshot'}">
          ${fullImageUrl
            ? `<img src="${fullImageUrl}" class="bookmark-thumb" alt="Screenshot" onerror="this.parentElement.innerHTML='<span class=\\'bookmark-thumb-placeholder\\'>🌐</span>'">`
            : '<span class="bookmark-thumb-placeholder">🔖</span>'}
        </div>
        <div class="bookmark-content">
          <div class="bookmark-title-row">
            <a href="${b.url || '#'}" class="bookmark-title" title="${escapeHtml(b.title || 'Untitled')}">
              ${escapeHtml(b.title || 'Untitled')}
            </a>
            <div class="bookmark-actions">
              ${b.url ? `<button class="item-action-btn copy-url-btn" data-url="${escapeHtml(b.url)}" title="Copy Link">📋</button>` : ''}
              <button class="item-action-btn delete-btn" data-id="${b.id}" title="Delete Bookmark">🗑️</button>
            </div>
          </div>
          ${domain ? `<span class="bookmark-domain">${escapeHtml(domain)}</span>` : ''}
          ${b.description ? `<p class="bookmark-desc">${escapeHtml(b.description)}</p>` : ''}
          ${tags.length > 0 ? `
            <div class="bookmark-tags-row">
              ${tags.map(t => `<span class="tag-chip" data-tag="${escapeHtml(t)}">${escapeHtml(t)}</span>`).join('')}
            </div>
          ` : ''}
        </div>
      </div>
    `;
  }).join('');

  // Attach card event listeners
  bookmarksList.querySelectorAll('.bookmark-title').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const href = link.getAttribute('href');
      if (href && href !== '#') {
        chrome.tabs.create({ url: href });
      }
    });
  });

  bookmarksList.querySelectorAll('.bookmark-thumb-wrap').forEach(wrap => {
    wrap.addEventListener('click', () => {
      const img = wrap.querySelector('img');
      if (img && img.src) {
        chrome.tabs.create({ url: img.src });
      }
    });
  });

  bookmarksList.querySelectorAll('.copy-url-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const url = btn.getAttribute('data-url');
      if (url) {
        await navigator.clipboard.writeText(url);
        const originalText = btn.textContent;
        btn.textContent = '✓';
        setTimeout(() => { btn.textContent = originalText; }, 1200);
      }
    });
  });

  bookmarksList.querySelectorAll('.delete-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const id = btn.getAttribute('data-id');
      if (id && confirm('Delete this bookmark?')) {
        btn.disabled = true;
        const res = await chrome.runtime.sendMessage({ action: 'delete-bookmark', id });
        if (res && res.success) {
          const card = btn.closest('.bookmark-card');
          if (card) card.remove();
          showBanner('Bookmark deleted', 'info');
          // Update count
          const currentCount = parseInt(bookmarkCount.textContent, 10) || 1;
          bookmarkCount.textContent = Math.max(0, currentCount - 1);
        } else {
          showBanner('Failed to delete bookmark', 'error');
          btn.disabled = false;
        }
      }
    });
  });

  bookmarksList.querySelectorAll('.tag-chip').forEach(chip => {
    chip.addEventListener('click', (e) => {
      e.stopPropagation();
      const tag = chip.getAttribute('data-tag');
      searchInput.value = tag;
      executeSearch(tag, true);
    });
  });
}

function extractAndRenderTags(bookmarks) {
  if (!bookmarks) return;
  const tagSet = new Set();
  bookmarks.forEach(b => {
    if (b.tags) {
      b.tags.split(',').forEach(t => {
        const clean = t.trim();
        if (clean) tagSet.add(clean);
      });
    }
  });

  const sortedTags = Array.from(tagSet).sort().slice(0, 10);
  if (sortedTags.length === 0) {
    tagPillsContainer.innerHTML = '';
    return;
  }

  tagPillsContainer.innerHTML = sortedTags.map(tag => `
    <span class="tag-pill ${activeTagFilter === tag ? 'active' : ''}" data-tag="${escapeHtml(tag)}">${escapeHtml(tag)}</span>
  `).join('');

  tagPillsContainer.querySelectorAll('.tag-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      const tag = pill.getAttribute('data-tag');
      if (activeTagFilter === tag) {
        activeTagFilter = null;
        pill.classList.remove('active');
        searchInput.value = '';
        loadRecentBookmarks();
      } else {
        activeTagFilter = tag;
        tagPillsContainer.querySelectorAll('.tag-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        searchInput.value = tag;
        executeSearch(tag, true);
      }
    });
  });
}

function setupEventListeners() {
  // Quick Bookmark
  quickBookmarkBtn.addEventListener('click', async () => {
    if (!activeTab) return;
    setButtonsDisabled(true);
    showBanner('Saving bookmark...', 'info');

    const res = await chrome.runtime.sendMessage({
      action: 'quick-bookmark',
      data: {
        url: activeTab.url,
        title: activeTab.title,
        tags: tagsInput.value.trim(),
        description: notesInput.value.trim()
      }
    });

    setButtonsDisabled(false);
    if (res && res.success) {
      showBanner(`✓ Saved: ${res.bookmark.title}`, 'success');
      bookmarkedBadge.classList.remove('hidden');
      quickBookmarkBtn.querySelector('.btn-label').textContent = 'Saved';
      await loadRecentBookmarks();
    } else {
      showBanner(`Failed to save: ${res?.error || 'Server error'}`, 'error');
    }
  });

  // Capture Tab Screenshot
  captureTabBtn.addEventListener('click', async () => {
    if (!activeTab) return;
    setButtonsDisabled(true);
    showBanner('Capturing tab and analyzing with OCR...', 'info');

    const res = await chrome.runtime.sendMessage({
      action: 'capture-visible',
      options: {
        url: activeTab.url,
        title: activeTab.title,
        tags: tagsInput.value.trim(),
        description: notesInput.value.trim()
      }
    });

    setButtonsDisabled(false);
    if (res && res.success) {
      showBanner(`✓ Screenshot bookmarked: ${res.bookmark.title}`, 'success');
      bookmarkedBadge.classList.remove('hidden');
      await loadRecentBookmarks();
    } else {
      showBanner(`Capture failed: ${res?.error || 'Check server connection'}`, 'error');
    }
  });

  // Capture Area
  captureAreaBtn.addEventListener('click', async () => {
    showBanner('Select an area on the page...', 'info');
    await chrome.runtime.sendMessage({ action: 'start-area-selection' });
    setTimeout(() => { window.close(); }, 200);
  });

  // Search input live filtering
  searchInput.addEventListener('input', () => {
    const q = searchInput.value.trim();
    clearSearchBtn.classList.toggle('hidden', !q);
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
      executeSearch(q, false);
    }, 220);
  });

  clearSearchBtn.addEventListener('click', () => {
    searchInput.value = '';
    clearSearchBtn.classList.add('hidden');
    activeTagFilter = null;
    tagPillsContainer.querySelectorAll('.tag-pill').forEach(p => p.classList.remove('active'));
    sectionTitle.textContent = 'Recent Bookmarks';
    loadRecentBookmarks();
  });

  // Settings drawer toggling
  settingsToggleBtn.addEventListener('click', () => {
    settingsPanel.classList.toggle('hidden');
  });

  closeSettingsBtn.addEventListener('click', () => {
    settingsPanel.classList.add('hidden');
  });

  saveSettingsBtn.addEventListener('click', async () => {
    const newBase = apiBaseInput.value.trim();
    if (!newBase) return;
    apiBase = newBase.replace(/\/+$/, '');
    await chrome.runtime.sendMessage({ action: 'set-config', apiBase });
    openWebUiLink.href = apiBase;
    showBanner('Settings saved! Checking connection...', 'info');
    const isOnline = await checkServerHealth();
    if (isOnline) {
      showBanner('Connected to server successfully!', 'success');
      settingsPanel.classList.add('hidden');
      loadRecentBookmarks();
    } else {
      showBanner(`Could not reach ${apiBase}`, 'error');
    }
  });
}

async function executeSearch(query, isTag = false) {
  if (!query) {
    sectionTitle.textContent = 'Recent Bookmarks';
    loadRecentBookmarks();
    return;
  }

  sectionTitle.textContent = isTag ? `Tag: "${query}"` : `Search: "${query}"`;
  bookmarksList.innerHTML = '<div class="loading-state">Searching...</div>';

  try {
    const res = await chrome.runtime.sendMessage({
      action: 'search-bookmarks',
      query: isTag ? '' : query,
      tag: isTag ? query : ''
    });

    if (res && res.success) {
      renderBookmarks(res.results);
    } else {
      bookmarksList.innerHTML = '<div class="empty-state">No matching bookmarks found.</div>';
    }
  } catch (err) {
    bookmarksList.innerHTML = '<div class="empty-state">Search error. Server might be offline.</div>';
  }
}

function setButtonsDisabled(disabled) {
  quickBookmarkBtn.disabled = disabled;
  captureTabBtn.disabled = disabled;
  captureAreaBtn.disabled = disabled;
}

function showBanner(message, type = 'info') {
  statusBanner.textContent = message;
  statusBanner.className = `status-banner ${type}`;
  statusBanner.classList.remove('hidden');

  setTimeout(() => {
    statusBanner.classList.add('hidden');
  }, 4500);
}

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}