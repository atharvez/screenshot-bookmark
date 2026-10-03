// Background Service Worker for Screenshot Bookmark Extension (Manifest V3)

const DEFAULT_API_BASE = 'http://localhost:8000';

async function getApiBase() {
  try {
    const data = await chrome.storage.local.get(['apiBase']);
    return (data.apiBase || DEFAULT_API_BASE).replace(/\/+$/, '');
  } catch (e) {
    return DEFAULT_API_BASE;
  }
}

// Setup context menus on installation
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'sb-quick-bookmark',
    title: '⭐ Quick Bookmark this page',
    contexts: ['page']
  });
  chrome.contextMenus.create({
    id: 'sb-capture-tab',
    title: '📷 Capture Tab Screenshot Bookmark',
    contexts: ['page']
  });
  chrome.contextMenus.create({
    id: 'sb-capture-area',
    title: '✂️ Capture Area Screenshot Bookmark',
    contexts: ['page']
  });
  chrome.contextMenus.create({
    id: 'sb-bookmark-selection',
    title: '📝 Bookmark Selected Text',
    contexts: ['selection']
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (!tab || !tab.id) return;

  if (info.menuItemId === 'sb-quick-bookmark') {
    await quickBookmarkTab(tab);
  } else if (info.menuItemId === 'sb-capture-tab') {
    await captureVisibleTab(tab);
  } else if (info.menuItemId === 'sb-capture-area') {
    await startAreaSelection(tab.id);
  } else if (info.menuItemId === 'sb-bookmark-selection') {
    await quickBookmarkTab(tab, { description: info.selectionText });
  }
});

// Handle keyboard shortcuts
chrome.commands.onCommand.addListener(async (command) => {
  const tab = await getCurrentTab();
  if (!tab) return;

  if (command === 'capture-screenshot') {
    await captureVisibleTab(tab);
  } else if (command === 'capture-area') {
    await startAreaSelection(tab.id);
  } else if (command === 'quick-bookmark') {
    await quickBookmarkTab(tab);
  }
});

// Listen for messages from popup or content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'capture-visible') {
    getCurrentTab().then(tab => captureVisibleTab(tab, request.options)).then(sendResponse);
    return true;
  } else if (request.action === 'start-area-selection') {
    getCurrentTab().then(tab => startAreaSelection(tab.id)).then(sendResponse);
    return true;
  } else if (request.action === 'capture-area-region') {
    handleAreaRegionCaptured(request.rect, request.tabInfo, sender.tab).then(sendResponse);
    return true;
  } else if (request.action === 'quick-bookmark') {
    getCurrentTab().then(tab => quickBookmarkTab(tab, request.data)).then(sendResponse);
    return true;
  } else if (request.action === 'check-url') {
    checkBookmarkStatus(request.url).then(sendResponse);
    return true;
  } else if (request.action === 'search-bookmarks') {
    searchBookmarks(request.query, request.tag).then(sendResponse);
    return true;
  } else if (request.action === 'get-recent') {
    getRecentBookmarks(request.limit).then(sendResponse);
    return true;
  } else if (request.action === 'delete-bookmark') {
    deleteBookmark(request.id).then(sendResponse);
    return true;
  } else if (request.action === 'update-bookmark') {
    updateBookmark(request.id, request.data).then(sendResponse);
    return true;
  } else if (request.action === 'get-config') {
    getApiBase().then(apiBase => sendResponse({ apiBase }));
    return true;
  } else if (request.action === 'set-config') {
    chrome.storage.local.set({ apiBase: request.apiBase }).then(() => sendResponse({ success: true }));
    return true;
  }
  return false;
});

async function getCurrentTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

async function startAreaSelection(tabId) {
  try {
    // Send message to content script (it is pre-injected via manifest)
    try {
      await chrome.tabs.sendMessage(tabId, { action: 'start-area-selection' });
      return { success: true };
    } catch (err) {
      // Fallback: inject content script if not already injected
      await chrome.scripting.executeScript({
        target: { tabId: tabId },
        files: ['content.js']
      });
      await chrome.tabs.sendMessage(tabId, { action: 'start-area-selection' });
      return { success: true };
    }
  } catch (error) {
    console.error('Failed to start area selection:', error);
    return { success: false, error: error.message };
  }
}

async function captureVisibleTab(tab, extraOptions = {}) {
  try {
    if (!tab) tab = await getCurrentTab();
    if (!tab || !tab.id) throw new Error('No active tab found');

    const dataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, { format: 'png' });
    const blob = await (await fetch(dataUrl)).blob();

    const title = extraOptions.title || tab.title || '';
    const url = extraOptions.url || tab.url || '';
    const description = extraOptions.description || '';
    const tags = extraOptions.tags || '';

    const result = await uploadScreenshotBlob(blob, {
      title,
      url,
      description,
      tags,
      filename: `screenshot_${Date.now()}.png`
    });

    if (result.success) {
      flashBadge('✓', '#16a34a');
      showNotification('Screenshot Bookmarked', `Saved: ${result.bookmark.title || title}`);
    }
    return result;
  } catch (error) {
    console.error('Capture visible tab failed:', error);
    flashBadge('!', '#dc2626');
    return { success: false, error: error.message };
  }
}

async function handleAreaRegionCaptured(rect, tabInfo, senderTab) {
  try {
    const tab = senderTab || await getCurrentTab();
    const dataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, { format: 'png' });

    // Crop image using OffscreenCanvas
    const croppedBlob = await cropImage(dataUrl, rect);

    const title = tabInfo?.title || tab.title || '';
    const url = tabInfo?.url || tab.url || '';
    const description = tabInfo?.metadata?.description || '';

    const result = await uploadScreenshotBlob(croppedBlob, {
      title,
      url,
      description,
      filename: `area_${Date.now()}.png`
    });

    if (result.success) {
      flashBadge('✓', '#16a34a');
      showNotification('Area Bookmarked', `Saved: ${result.bookmark.title || title}`);
    }
    return result;
  } catch (error) {
    console.error('Area capture handling failed:', error);
    flashBadge('!', '#dc2626');
    return { success: false, error: error.message };
  }
}

async function cropImage(dataUrl, rect) {
  try {
    const response = await fetch(dataUrl);
    const blob = await response.blob();
    const bitmap = await createImageBitmap(blob);

    const dpr = rect.devicePixelRatio || 1;
    const sx = Math.max(0, Math.round(rect.x * dpr));
    const sy = Math.max(0, Math.round(rect.y * dpr));
    const sw = Math.min(bitmap.width - sx, Math.round(rect.width * dpr));
    const sh = Math.min(bitmap.height - sy, Math.round(rect.height * dpr));

    if (sw <= 0 || sh <= 0) {
      return blob; // fallback to original if zero sized
    }

    const canvas = new OffscreenCanvas(sw, sh);
    const ctx = canvas.getContext('2d');
    ctx.drawImage(bitmap, sx, sy, sw, sh, 0, 0, sw, sh);

    return await canvas.convertToBlob({ type: 'image/png' });
  } catch (err) {
    console.warn('Canvas cropping failed, using full image:', err);
    const res = await fetch(dataUrl);
    return await res.blob();
  }
}

async function quickBookmarkTab(tab, customData = {}) {
  try {
    if (!tab) tab = await getCurrentTab();
    const apiBase = await getApiBase();

    const payload = {
      url: customData.url || tab.url || '',
      title: customData.title || tab.title || 'Untitled',
      description: customData.description || '',
      tags: customData.tags || ''
    };

    const response = await fetch(`${apiBase}/api/bookmarks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(`Server returned ${response.status}`);
    }

    const result = await response.json();
    flashBadge('★', '#2563eb');
    showNotification('Page Bookmarked', `Saved: ${result.title}`);
    return { success: true, bookmark: result };
  } catch (error) {
    console.error('Quick bookmark failed:', error);
    flashBadge('!', '#dc2626');
    return { success: false, error: error.message };
  }
}

async function uploadScreenshotBlob(blob, metadata) {
  try {
    const apiBase = await getApiBase();
    const formData = new FormData();
    formData.append('file', blob, metadata.filename || 'screenshot.png');

    if (metadata.title) formData.append('title', metadata.title);
    if (metadata.url) formData.append('url', metadata.url);
    if (metadata.description) formData.append('description', metadata.description);
    if (metadata.tags) formData.append('tags', metadata.tags);

    const response = await fetch(`${apiBase}/api/upload`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error(`Upload failed with status ${response.status}`);
    }

    const bookmark = await response.json();
    return { success: true, bookmark };
  } catch (error) {
    console.error('Upload failed:', error);
    return { success: false, error: error.message };
  }
}

async function checkBookmarkStatus(url) {
  try {
    const apiBase = await getApiBase();
    const response = await fetch(`${apiBase}/api/check?url=${encodeURIComponent(url)}`);
    if (response.ok) {
      return await response.json();
    }
    return { bookmarked: false, bookmark: null };
  } catch (e) {
    return { bookmarked: false, bookmark: null, error: e.message };
  }
}

async function searchBookmarks(query, tag) {
  try {
    const apiBase = await getApiBase();
    let url = `${apiBase}/api/search?limit=25`;
    if (tag) url += `&tag=${encodeURIComponent(tag)}`;
    if (query) url += `&q=${encodeURIComponent(query)}`;

    const response = await fetch(url);
    if (!response.ok) throw new Error(`Search failed: ${response.status}`);
    const data = await response.json();
    return { success: true, results: data.results };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

async function getRecentBookmarks(limit = 20) {
  try {
    const apiBase = await getApiBase();
    const response = await fetch(`${apiBase}/api/recent?limit=${limit}`);
    if (!response.ok) throw new Error(`Failed to fetch recent: ${response.status}`);
    const bookmarks = await response.json();
    return { success: true, bookmarks };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

async function deleteBookmark(id) {
  try {
    const apiBase = await getApiBase();
    const response = await fetch(`${apiBase}/api/bookmark/${id}`, { method: 'DELETE' });
    if (!response.ok) throw new Error(`Delete failed: ${response.status}`);
    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

async function updateBookmark(id, data) {
  try {
    const apiBase = await getApiBase();
    const response = await fetch(`${apiBase}/api/bookmark/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error(`Update failed: ${response.status}`);
    const bookmark = await response.json();
    return { success: true, bookmark };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

function flashBadge(text, color) {
  chrome.action.setBadgeText({ text });
  chrome.action.setBadgeBackgroundColor({ color });
  setTimeout(() => {
    chrome.action.setBadgeText({ text: '' });
  }, 2500);
}

function showNotification(title, message) {
  try {
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icons/icon48.png',
      title: title,
      message: message
    });
  } catch (e) {
    console.log('Notification error:', e);
  }
}