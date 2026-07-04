/**
 * Claude Interceptor
 *
 * Captures conversations from claude.ai
 */

class ClaudeInterceptor extends BaseInterceptor {
  constructor() {
    super("claude");
    this.processedMessages = new Set();
  }

  onDOMChange(mutations) {
    // Claude uses different selectors
    const messages = document.querySelectorAll('[data-is-streaming], .font-claude-message');

    messages.forEach((messageEl) => {
      const messageId = this.getMessageId(messageEl);

      if (!this.processedMessages.has(messageId)) {
        this.processedMessages.add(messageId);

        const message = this.extractMessage(messageEl);
        if (message) {
          this.sendToRAE(message);
        }
      }
    });
  }

  extractMessage(element) {
    try {
      // Determine role from element classes or parent structure
      const isUser = element.closest('[data-test-render-count]') || element.classList.contains('user-message');
      const role = isUser ? 'user' : 'assistant';

      const content = element.innerText.trim();

      if (content.length === 0) return null;

      return {
        role: role,
        content: content,
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      console.error('[RAE] Error extracting Claude message:', error);
      return null;
    }
  }

  getMessageId(element) {
    const content = element.innerText.substring(0, 100);
    const position = Array.from(document.querySelectorAll('[data-is-streaming], .font-claude-message')).indexOf(element);
    return `${content}-${position}`;
  }
}

// Initialize interceptor
if (window.location.hostname === 'claude.ai') {
  const interceptor = new ClaudeInterceptor();
  interceptor.init();
}
