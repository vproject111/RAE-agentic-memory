/**
 * Background Service Worker
 *
 * Handles extension lifecycle and communication.
 */

console.log('[RAE] Service worker loaded');

// Default settings
const DEFAULT_SETTINGS = {
  enabled: true,
  raeEndpoint: 'http://localhost:8765/memories',
  captureChats: true,
  autoSync: false,
};

// Initialize settings on install
chrome.runtime.onInstalled.addListener(async () => {
  console.log('[RAE] Extension installed');

  // Set default settings
  await chrome.storage.sync.set(DEFAULT_SETTINGS);

  // Show welcome notification
  chrome.notifications.create({
    type: 'basic',
    iconUrl: '/icons/icon48.png',
    title: 'RAE Memory Capture',
    message: 'Extension installed! Start chatting to capture conversations.',
  });
});

// Handle messages from content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[RAE] Received message:', message);

  if (message.type === 'content-ready') {
    console.log('[RAE] Content script ready on:', message.url);
    sendResponse({ status: 'acknowledged' });
  }

  if (message.type === 'memory-captured') {
    console.log('[RAE] Memory captured:', message.data);
    // Could add additional processing here
    sendResponse({ status: 'received' });
  }

  return true; // Keep message channel open for async response
});

// Handle extension icon click
chrome.action.onClicked.addListener((tab) => {
  console.log('[RAE] Extension icon clicked on tab:', tab.id);
});

// Badge to show extension is active
chrome.action.setBadgeText({ text: 'ON' });
chrome.action.setBadgeBackgroundColor({ color: '#2563eb' });
