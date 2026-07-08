/**
* Custom hook for managing video file upload state.
*/
import { useState, useCallback } from 'react';
import { validateFile, getVideoDuration } from '../utils/helpers';

export function useUpload() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState(null);

  const handleFileSelect = useCallback(async (selectedFile) => {
    const validation = validateFile(selectedFile);
    if (!validation.valid) {
      setError(validation.error);
      return;
    }

    if (preview) {
      URL.revokeObjectURL(preview);
    }

    const previewUrl = URL.createObjectURL(selectedFile);
    setFile(selectedFile);
    setPreview(previewUrl);
    setError(null);

    getVideoDuration(selectedFile)
      .then(setDuration)
      .catch(() => setDuration(0));
  }, [preview]);

  const clearFile = useCallback(() => {
    if (preview) {
      URL.revokeObjectURL(preview);
    }
    setFile(null);
    setPreview(null);
    setDuration(0);
    setError(null);
  }, [preview]);

  return {
    file,
    preview,
    duration,
    error,
    handleFileSelect,
    clearFile,
    setError,
  };
}
