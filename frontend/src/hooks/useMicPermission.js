import { useState, useEffect } from 'react';

/**
 * Lightweight hook for proactive microphone permission status check.
 * Uses navigator.permissions.query if available, otherwise falls back gracefully.
 *
 * Returns:
 *   status: 'granted' | 'denied' | 'prompt' | 'unsupported' | 'checking'
 *   requestPermission: async function to trigger microphone permission dialog
 */
export function useMicPermission() {
  const [status, setStatus] = useState('checking');

  useEffect(() => {
    if (
      typeof navigator === 'undefined' ||
      !navigator.permissions ||
      !navigator.permissions.query
    ) {
      setStatus('unsupported');
      return;
    }

    let permissionStatus = null;

    navigator.permissions
      .query({ name: 'microphone' })
      .then((result) => {
        permissionStatus = result;
        setStatus(result.state);
        result.onchange = () => {
          setStatus(result.state);
        };
      })
      .catch(() => {
        setStatus('unsupported');
      });

    return () => {
      if (permissionStatus) {
        permissionStatus.onchange = null;
      }
    };
  }, []);

  const requestPermission = async () => {
    if (typeof navigator === 'undefined' || !navigator.mediaDevices) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((t) => t.stop());
      setStatus('granted');
    } catch (err) {
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setStatus('denied');
      }
    }
  };

  return { status, requestPermission };
}

export default useMicPermission;
