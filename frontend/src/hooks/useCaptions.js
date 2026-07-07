/**
 * Custom hook for managing caption generation state.
 */
import { useState, useCallback } from 'react';
import { generateCaptions } from '../services/api';

export function useCaptions() {
  const [captions, setCaptions] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [phase, setPhase] = useState('idle'); // idle | uploading | processing | done | error
  const [error, setError] = useState(null);

  const generate = useCallback(async (file, styles) => {
    setIsLoading(true);
    setUploadProgress(0);
    setPhase('uploading');
    setError(null);
    setCaptions(null);

    try {
      const result = await generateCaptions(file, styles, (progress) => {
        setUploadProgress(progress);
        if (progress >= 100) {
          setPhase('processing');
        }
      });

      setCaptions(result);
      setPhase('done');
    } catch (err) {
      setError(err.message);
      setPhase('error');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setCaptions(null);
    setIsLoading(false);
    setUploadProgress(0);
    setPhase('idle');
    setError(null);
  }, []);

  return {
    captions,
    isLoading,
    uploadProgress,
    phase,
    error,
    generate,
    reset,
  };
}
