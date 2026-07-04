/**
 * Base Interceptor for AI Chat Platforms
 *
 * Provides common functionality for capturing conversations.
 */

class BaseInterceptor {
  constructor(platform) {
    this.platform = platform;
    this.raeEndpoint = "http://localhost:8765/memories";
    this.isEnabled = true;
  }

  /**
   * Initialize the interceptor
   */
  async init() {
    console.log(`[RAE] ${this.platform} interceptor initialized`);
    this.loadSettings();
    this.startObserving();
  }

  /**
   * Load settings from chrome.storage
   */
  async loadSettings() {
    const settings = await chrome.storage.sync.get({
      enabled: true,
      raeEndpoint: "http://localhost:8765/memories",
    });

    this.isEnabled = settings.enabled;
    this.raeEndpoint = settings.raeEndpoint;
  }

  /**
   * Start observing DOM changes
   */
  startObserving() {
    const observer = new MutationObserver((mutations) => {
      this.onDOMChange(mutations);
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  }

  /**
   * Handle DOM changes (override in subclass)
   */
  onDOMChange(mutations) {
    // Override in subclass
  }

  /**
   * Extract conversation from message element (override in subclass)
   */
  extractMessage(element) {
    // Override in subclass
    return null;
  }

  /**
   * Send message to RAE
   */
  async sendToRAE(message) {
    if (!this.isEnabled) return;

    try {
      const response = await fetch(this.raeEndpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          content: message.content,
          source: `browser-${this.platform}`,
          project: "browser-captures",
          importance: 0.7,
          tags: [this.platform, message.role],
        }),
      });

      if (response.ok) {
        console.log(`[RAE] Saved to ${this.platform}:`, message.content.substring(0, 100));
      } else {
        console.error(`[RAE] Failed to save:`, response.statusText);
      }
    } catch (error) {
      console.error(`[RAE] Error sending to RAE:`, error);
    }
  }

  /**
   * Debounce helper
   */
  debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }
}

// Make available globally
window.BaseInterceptor = BaseInterceptor;
