// Content script for Screenshot Bookmark
// Handles interactive area selection and page metadata extraction

let isSelecting = false;
let startX = 0, startY = 0, endX = 0, endY = 0;
let overlayEl = null, selectionBoxEl = null, infoBadgeEl = null;

// Listen for messages from background or popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'start-area-selection') {
    startAreaSelection();
    sendResponse({ success: true });
    return true;
  } else if (request.action === 'get-page-metadata') {
    const metadata = extractPageMetadata();
    sendResponse({ success: true, metadata });
    return true;
  }
  return false;
});

function extractPageMetadata() {
  const metaDesc = document.querySelector('meta[name="description"]') ||
                   document.querySelector('meta[property="og:description"]');
  const description = metaDesc ? metaDesc.getAttribute('content') || '' : '';

  const faviconLink = document.querySelector('link[rel="icon"]') ||
                      document.querySelector('link[rel="shortcut icon"]');
  const favicon = faviconLink ? faviconLink.href : '';

  const selectedText = window.getSelection ? window.getSelection().toString().trim() : '';

  return {
    url: window.location.href,
    title: document.title || window.location.hostname,
    description: selectedText || description,
    selectedText: selectedText,
    favicon: favicon
  };
}

function startAreaSelection() {
  if (isSelecting) return;
  isSelecting = true;

  // Create backdrop overlay
  overlayEl = document.createElement('div');
  overlayEl.id = 'sb-capture-overlay';
  overlayEl.style.cssText = `
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    background: rgba(15, 23, 42, 0.45) !important;
    cursor: crosshair !important;
    z-index: 2147483647 !important;
    user-select: none !important;
  `;

  // Selection rectangle
  selectionBoxEl = document.createElement('div');
  selectionBoxEl.id = 'sb-capture-box';
  selectionBoxEl.style.cssText = `
    position: fixed !important;
    border: 2px solid #2563eb !important;
    background: rgba(37, 99, 235, 0.15) !important;
    box-shadow: 0 0 0 99999px rgba(0, 0, 0, 0.35), 0 0 12px rgba(37, 99, 235, 0.5) !important;
    border-radius: 4px !important;
    z-index: 2147483647 !important;
    pointer-events: none !important;
    display: none !important;
  `;

  // Info dimensions badge
  infoBadgeEl = document.createElement('div');
  infoBadgeEl.id = 'sb-capture-badge';
  infoBadgeEl.style.cssText = `
    position: fixed !important;
    bottom: 24px !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
    background: #1e293b !important;
    color: #f8fafc !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 8px 16px !important;
    border-radius: 20px !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
    z-index: 2147483647 !important;
    pointer-events: none !important;
  `;
  infoBadgeEl.textContent = 'Drag to select an area • Press ESC to cancel';

  overlayEl.appendChild(selectionBoxEl);
  overlayEl.appendChild(infoBadgeEl);
  document.documentElement.appendChild(overlayEl);

  overlayEl.addEventListener('mousedown', onMouseDown);
  document.addEventListener('keydown', onKeyDown);
}

function onMouseDown(e) {
  if (e.button !== 0) return; // Left click only
  startX = e.clientX;
  startY = e.clientY;
  endX = e.clientX;
  endY = e.clientY;

  selectionBoxEl.style.display = 'block';
  updateSelectionBox();

  document.addEventListener('mousemove', onMouseMove);
  document.addEventListener('mouseup', onMouseUp);
}

function onMouseMove(e) {
  endX = e.clientX;
  endY = e.clientY;
  updateSelectionBox();
}

function updateSelectionBox() {
  const x = Math.min(startX, endX);
  const y = Math.min(startY, endY);
  const width = Math.abs(endX - startX);
  const height = Math.abs(endY - startY);

  selectionBoxEl.style.left = `${x}px`;
  selectionBoxEl.style.top = `${y}px`;
  selectionBoxEl.style.width = `${width}px`;
  selectionBoxEl.style.height = `${height}px`;

  if (width > 0 && height > 0) {
    infoBadgeEl.textContent = `${width} × ${height} px • Release to capture`;
  }
}

function onMouseUp(e) {
  document.removeEventListener('mousemove', onMouseMove);
  document.removeEventListener('mouseup', onMouseUp);

  const rect = {
    x: Math.min(startX, endX),
    y: Math.min(startY, endY),
    width: Math.abs(endX - startX),
    height: Math.abs(endY - startY),
    devicePixelRatio: window.devicePixelRatio || 1
  };

  cleanup();

  // If selection is reasonably sized (> 10px in both dimensions)
  if (rect.width >= 10 && rect.height >= 10) {
    chrome.runtime.sendMessage({
      action: 'capture-area-region',
      rect: rect,
      tabInfo: {
        url: window.location.href,
        title: document.title,
        metadata: extractPageMetadata()
      }
    });
  }
}

function onKeyDown(e) {
  if (e.key === 'Escape') {
    cleanup();
  }
}

function cleanup() {
  isSelecting = false;
  document.removeEventListener('mousemove', onMouseMove);
  document.removeEventListener('mouseup', onMouseUp);
  document.removeEventListener('keydown', onKeyDown);

  if (overlayEl && overlayEl.parentNode) {
    overlayEl.parentNode.removeChild(overlayEl);
  }
  overlayEl = null;
  selectionBoxEl = null;
  infoBadgeEl = null;
}