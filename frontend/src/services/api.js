/**
 * API service — communicates with the FastAPI backend.
 */

const API_KEY = 'dev-key-123';

/**
 * Upload a video file and create a caption generation task.
 *
 * Uses XMLHttpRequest to enable upload progress tracking.
 *
 * @param {File} file - The video file to caption.
 * @param {string[]} styles - Array of style IDs to generate.
 * @param {function} onProgress - Callback with upload progress (0-100).
 * @returns {Promise<{task_id: string, status: string}>}
 */
export function uploadVideo(file, styles, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();

    formData.append('video', file);
    formData.append('styles', styles.join(','));

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        const percent = Math.round((e.loaded / e.total) * 100);
        onProgress(percent);
      }
    });

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

    xhr.addEventListener('error', () => {
      reject(new Error('Network error. Is the backend running on port 8000?'));
    });

    xhr.addEventListener('abort', () => {
      reject(new Error('Upload cancelled.'));
    });

    xhr.open('POST', '/v1/tasks/upload');
    xhr.setRequestHeader('X-API-Key', API_KEY);
    xhr.send(formData);
  });
}

/**
 * Poll a task for its current status and result.
 *
 * @param {string} taskId - The task ID to poll.
 * @returns {Promise<Object>} The task response with status and optional result.
 */
export async function pollTask(taskId) {
  const res = await fetch(`/v1/tasks/${taskId}`, {
    headers: { 'X-API-Key': API_KEY },
  });
  if (!res.ok) {
    let detail = '';
    try {
      const data = await res.json();
      detail = data.detail ? `: ${data.detail}` : '';
    } catch {
      detail = '';
    }
    throw new Error(`Failed to poll task: HTTP ${res.status}${detail}`);
  }
  return await res.json();
}

/**
 * Check if the backend is healthy.
 */
export async function checkHealth() {
  try {
    const res = await fetch('/health');
    if (!res.ok) throw new Error(`Status ${res.status}`);
    return await res.json();
  } catch (err) {
    throw new Error('Backend not reachable. Make sure the server is running.');
  }
}
