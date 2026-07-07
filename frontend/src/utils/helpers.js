/**
 * Utility helper functions.
 */
import { MAX_FILE_SIZE, ALLOWED_TYPES, ALLOWED_EXTENSIONS } from './constants';

/**
 * Format bytes into a human-readable file size string.
 */
export function formatFileSize(bytes) {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

/**
 * Format seconds into mm:ss string.
 */
export function formatDuration(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Count the number of words in a string.
 */
export function countWords(text) {
  if (!text) return 0;
  return text.trim().split(/\s+/).filter(Boolean).length;
}

/**
 * Validate a File object for type and size.
 * Returns { valid: boolean, error: string | null }.
 */
export function validateFile(file) {
  if (!file) {
    return { valid: false, error: 'No file selected.' };
  }

  // Check file type
  const ext = '.' + file.name.split('.').pop().toLowerCase();
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    return {
      valid: false,
      error: `Unsupported format "${ext}". Use: ${ALLOWED_EXTENSIONS.join(', ')}`,
    };
  }

  // Check MIME type if available
  if (file.type && !ALLOWED_TYPES.includes(file.type)) {
    // Allow if extension is valid but MIME is missing/different
    if (!file.type.startsWith('video/')) {
      return {
        valid: false,
        error: `Invalid file type "${file.type}". Please upload a video file.`,
      };
    }
  }

  // Check file size
  if (file.size > MAX_FILE_SIZE) {
    return {
      valid: false,
      error: `File too large (${formatFileSize(file.size)}). Maximum: ${formatFileSize(MAX_FILE_SIZE)}.`,
    };
  }

  return { valid: true, error: null };
}

/**
 * Get the video duration by loading it into a temporary video element.
 * Returns a promise that resolves with the duration in seconds.
 */
export function getVideoDuration(file) {
  return new Promise((resolve, reject) => {
    const video = document.createElement('video');
    video.preload = 'metadata';
    const url = URL.createObjectURL(file);

    video.onloadedmetadata = () => {
      URL.revokeObjectURL(url);
      resolve(video.duration);
    };

    video.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('Could not load video metadata.'));
    };

    video.src = url;
  });
}
