/**
 * API service — communicates with the FastAPI backend.
 */

/**
 * Generate captions for a video file.
 *
 * Uses XMLHttpRequest instead of fetch() to enable upload progress tracking.
 *
 * @param {File} file - The video file to caption.
 * @param {string[]} styles - Array of style IDs to generate.
 * @param {function} onProgress - Callback with upload progress (0-100).
 * @returns {Promise<Object>} The caption response JSON.
 */
export function generateCaptions(file, styles, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();

    formData.append('video', file);
    formData.append('styles', styles.join(','));

    // Track upload progress
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        const percent = Math.round((e.loaded / e.total) * 100);
        onProgress(percent);
      }
    });

    // Handle completion
    xhr.addEventListener('load', () => {
      try {
        const data = JSON.parse(xhr.responseText);
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(data);
        } else {
          reject(new Error(data.detail || `Server error (${xhr.status})`));
        }
      } catch {
        reject(new Error(`Invalid response from server (${xhr.status})`));
      }
    });

    // Handle network errors
    xhr.addEventListener('error', () => {
      reject(new Error('Network error. Is the backend running on port 8000?'));
    });

    xhr.addEventListener('abort', () => {
      reject(new Error('Upload cancelled.'));
    });

    xhr.open('POST', '/api/caption');
    xhr.send(formData);
  });
}

/**
 * Check if the backend is healthy.
 */
export async function checkHealth() {
  try {
    const res = await fetch('/api/health');
    if (!res.ok) throw new Error(`Status ${res.status}`);
    return await res.json();
  } catch (err) {
    throw new Error('Backend not reachable. Make sure the server is running.');
  }
}
