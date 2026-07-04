/**
 * Popup UI Script
 */

document.addEventListener('DOMContentLoaded', async () => {
  const enabledCheckbox = document.getElementById('enabledCheckbox');
  const endpointInput = document.getElementById('endpointInput');
  const saveButton = document.getElementById('saveButton');
  const statusIndicator = document.getElementById('statusIndicator');
  const statusText = document.getElementById('statusText');

  // Load current settings
  const settings = await chrome.storage.sync.get({
    enabled: true,
    raeEndpoint: 'http://localhost:8765/memories',
  });

  enabledCheckbox.checked = settings.enabled;
  endpointInput.value = settings.raeEndpoint;

  // Update status indicator
  if (settings.enabled) {
    statusIndicator.classList.remove('inactive');
    statusText.textContent = 'Active';
  } else {
    statusIndicator.classList.add('inactive');
    statusText.textContent = 'Inactive';
  }

  // Save settings
  saveButton.addEventListener('click', async () => {
    const newSettings = {
      enabled: enabledCheckbox.checked,
      raeEndpoint: endpointInput.value,
    };

    await chrome.storage.sync.set(newSettings);

    // Update status
    if (newSettings.enabled) {
      statusIndicator.classList.remove('inactive');
      statusText.textContent = 'Active';
      chrome.action.setBadgeText({ text: 'ON' });
    } else {
      statusIndicator.classList.add('inactive');
      statusText.textContent = 'Inactive';
      chrome.action.setBadgeText({ text: 'OFF' });
    }

    // Show saved feedback
    const originalText = saveButton.textContent;
    saveButton.textContent = 'Saved!';
    setTimeout(() => {
      saveButton.textContent = originalText;
    }, 1000);
  });

  // Update enabled checkbox changes status immediately
  enabledCheckbox.addEventListener('change', () => {
    if (enabledCheckbox.checked) {
      statusIndicator.classList.remove('inactive');
      statusText.textContent = 'Active';
    } else {
      statusIndicator.classList.add('inactive');
      statusText.textContent = 'Inactive';
    }
  });
});
