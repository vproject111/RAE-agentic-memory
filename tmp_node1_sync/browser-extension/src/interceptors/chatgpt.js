/**
 * ChatGPT Interceptor
 *
 * Captures conversations from chat.openai.com
 */

class ChatGPTInterceptor extends BaseInterceptor {
  constructor() {
    super("chatgpt");
    this.processedMessages = new Set();
  }

  onDOMChange(mutations) {
    const messages = document.querySelectorAll('[data-message-author-role]');

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
      const role = element.getAttribute('data-message-author-role');
      const contentEl = element.querySelector('.markdown, [class*="markdown"]');

      if (!contentEl) return null;

      const content = contentEl.innerText.trim();

      if (content.length === 0) return null;

      return {
        role: role,
        content: content,
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      console.error('[RAE] Error extracting ChatGPT message:', error);
      return null;
    }
  }

  getMessageId(element) {
    // Use element's text content + position as unique ID
    const content = element.innerText.substring(0, 100);
    const position = Array.from(document.querySelectorAll('[data-message-author-role]')).indexOf(element);
    return `${content}-${position}`;
  }
}

// Initialize interceptor
if (window.location.hostname === 'chat.openai.com') {
  const interceptor = new ChatGPTInterceptor();
  interceptor.init();
}
