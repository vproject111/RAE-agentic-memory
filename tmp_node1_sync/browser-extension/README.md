# RAE Memory Capture - Browser Extension

Capture AI conversations from ChatGPT, Claude, Gemini and other platforms directly into RAE-Lite or RAE-Server.

## Features

- **Multi-platform support**: ChatGPT, Claude, Gemini (Grok, DeepSeek coming soon)
- **Automatic capture**: Conversations saved in real-time
- **Local-first**: Works with RAE-Lite (localhost:8765)
- **Server support**: Can connect to RAE-Server
- **Simple UI**: Enable/disable capture, configure endpoint

## Installation

### Development Mode

1. Open Chrome/Edge and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top-right)
3. Click "Load unpacked"
4. Select the `browser-extension` directory

### Firefox

1. Navigate to `about:debugging#/runtime/this-firefox`
2. Click "Load Temporary Add-on"
3. Select `manifest.json` from `browser-extension` directory

## Usage

1. **Start RAE-Lite** (or ensure RAE-Server is running)
   ```bash
   rae-lite
   ```

2. **Navigate to a supported platform**:
   - https://chat.openai.com
   - https://claude.ai
   - https://gemini.google.com

3. **Start chatting** - conversations are automatically captured

4. **Check the extension popup** to verify it's active

## Configuration

Click the extension icon to open settings:

- **Enable memory capture**: Toggle on/off
- **RAE Endpoint**: Default is `http://localhost:8765/memories` (RAE-Lite)
- For RAE-Server: Use your server URL (e.g., `https://your-server.com/v2/memories`)

## Architecture

```
browser-extension/
├── manifest.json           # Extension configuration (Manifest V3)
├── src/
│   ├── background/
│   │   └── service-worker.js   # Background service worker
│   ├── content/
│   │   └── injector.js         # Content script coordinator
│   ├── interceptors/
│   │   ├── base.js             # Base interceptor class
│   │   ├── chatgpt.js          # ChatGPT-specific
│   │   ├── claude.js           # Claude-specific
│   │   └── gemini.js           # Gemini-specific
│   └── popup/
│       ├── popup.html          # Settings UI
│       └── popup.js            # Settings logic
└── icons/
    ├── icon16.png
    ├── icon48.png
    └── icon128.png
```

## Supported Platforms

### Currently Implemented
- ✅ ChatGPT (chat.openai.com)
- ✅ Claude (claude.ai)
- ✅ Gemini (gemini.google.com)

### Coming Soon (Phase 4 Week 12)
- 🔜 Grok (grok.x.com)
- 🔜 DeepSeek (chat.deepseek.com)
- 🔜 Perplexity
- 🔜 You.com

## Privacy

- All data is stored locally (if using RAE-Lite)
- No external tracking or analytics
- You control where data is sent
- Open source and auditable

## Development

### Adding a New Platform

1. Create `src/interceptors/platform-name.js`
2. Extend `BaseInterceptor` class
3. Implement `extractMessage()` and `onDOMChange()`
4. Add to `manifest.json` content_scripts
5. Test on target platform

Example:
```javascript
class NewPlatformInterceptor extends BaseInterceptor {
  constructor() {
    super("platform-name");
  }

  extractMessage(element) {
    // Platform-specific extraction logic
  }
}
```

### Testing

1. Load extension in developer mode
2. Open browser console (F12)
3. Look for `[RAE]` log messages
4. Verify messages reach RAE endpoint

## Publishing

### Chrome Web Store
- Package as .zip
- Create developer account
- Submit for review

### Firefox Add-ons
- Package as .xpi
- Create AMO account
- Submit for review

## License

Same as RAE-agentic-memory project.

## Version

Current: 0.1.0 (Phase 4 Week 11)
