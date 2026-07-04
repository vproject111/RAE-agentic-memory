/**
 * Content Script Injector
 *
 * Coordinates between page scripts and background service worker.
 */

console.log('[RAE] Content script loaded');

// Listen for messages from interceptors
window.addEventListener('rae-memory-captured', (event) => {
  console.log('[RAE] Memory captured:', event.detail);

  // Forward to background service worker
  chrome.runtime.sendMessage({
    type: 'memory-captured',
    data: event.detail,
  });
});

// Listen for messages from background
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'get-status') {
    sendResponse({ status: 'active', platform: window.location.hostname });
  }
});

// Notify background that content script is ready
chrome.runtime.sendMessage({
  type: 'content-ready',
  url: window.location.href,
});
