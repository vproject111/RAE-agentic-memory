/**
 * Gemini Interceptor
 *
 * Captures conversations from gemini.google.com
 */

class GeminiInterceptor extends BaseInterceptor {
  constructor() {
    super("gemini");
    this.processedMessages = new Set();
  }

  onDOMChange(mutations) {
    const messages = document.querySelectorAll('.model-response-text, .user-query');

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
      const isUser = element.classList.contains('user-query');
      const role = isUser ? 'user' : 'assistant';

      const content = element.innerText.trim();

      if (content.length === 0) return null;

      return {
        role: role,
        content: content,
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      console.error('[RAE] Error extracting Gemini message:', error);
      return null;
    }
  }

  getMessageId(element) {
    const content = element.innerText.substring(0, 100);
    const position = Array.from(document.querySelectorAll('.model-response-text, .user-query')).indexOf(element);
    return `${content}-${position}`;
  }
}

// Initialize interceptor
if (window.location.hostname === 'gemini.google.com') {
  const interceptor = new GeminiInterceptor();
  interceptor.init();
}
