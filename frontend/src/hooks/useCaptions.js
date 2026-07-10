/**
 * Custom hook for managing caption generation state.
 * Handles file upload + async polling for task completion.
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import { uploadVideo, pollTask } from '../services/api';

const POLL_INTERVAL_MS = 3000;
const MAX_POLL_MS = 5 * 60 * 1000;

export function useCaptions() {
  const [captions, setCaptions] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [phase, setPhase] = useState('idle');
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);
  const pollStartedAtRef = useRef(null);

  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        pollStartedAtRef.current = null;
      }
    };
  }, []);

  const startPolling = useCallback((taskId) => {
    pollStartedAtRef.current = Date.now();

    const stopWithError = (message) => {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
      pollStartedAtRef.current = null;
      setError(message);
      setPhase('error');
      setIsLoading(false);
    };

    intervalRef.current = setInterval(async () => {
      if (Date.now() - pollStartedAtRef.current > MAX_POLL_MS) {
        stopWithError(`Caption generation timed out for task ${taskId}. Please retry.`);
        return;
      }

      try {
        const task = await pollTask(taskId);

        if (task.status === 'COMPLETED') {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
          pollStartedAtRef.current = null;
          setCaptions(task.result);
          setPhase('done');
          setIsLoading(false);
        } else if (task.status === 'FAILED') {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
          pollStartedAtRef.current = null;
          setError(task.error_message || 'Video processing failed.');
          setPhase('error');
          setIsLoading(false);
        } else if (!['PENDING', 'PROCESSING'].includes(task.status)) {
          stopWithError(`Unexpected task status: ${task.status}`);
        }
      } catch (err) {
        stopWithError(err.message);
      }
    }, POLL_INTERVAL_MS);
  }, []);

  const generate = useCallback(async (file, styles) => {
    setIsLoading(true);
    setUploadProgress(0);
    setPhase('uploading');
    setError(null);
    setCaptions(null);

    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
      pollStartedAtRef.current = null;
    }

    try {
      const result = await uploadVideo(file, styles, (progress) => {
        setUploadProgress(progress);
        if (progress >= 100) {
          setPhase('processing');
        }
      });

      setPhase('processing');
      startPolling(result.task_id);
    } catch (err) {
      setError(err.message);
      setPhase('error');
      setIsLoading(false);
    }
  }, [startPolling]);

  const reset = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
      pollStartedAtRef.current = null;
    }
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
