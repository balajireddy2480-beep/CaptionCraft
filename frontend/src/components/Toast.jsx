/**
 * Toast — Slide-in notification for errors and success messages.
 */
import { useEffect, useState } from 'react';

const VARIANTS = {
  error: {
    bg: 'bg-error/15 border-error/30',
    text: 'text-error',
    icon: '✕',
  },
  success: {
    bg: 'bg-success/15 border-success/30',
    text: 'text-success',
    icon: '✓',
  },
  warning: {
    bg: 'bg-style-sarcastic/15 border-style-sarcastic/30',
    text: 'text-style-sarcastic',
    icon: '⚠',
  },
};

export default function Toast({ message, variant = 'error', onClose, duration = 4000 }) {
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    if (!message) return;

    const timer = setTimeout(() => {
      setIsExiting(true);
      setTimeout(onClose, 300);
    }, duration);

    return () => clearTimeout(timer);
  }, [message, duration, onClose]);

  if (!message) return null;

  const v = VARIANTS[variant] || VARIANTS.error;

  return (
    <div className="fixed top-6 right-6 z-50 max-w-sm">
      <div
        className={`
          flex items-start gap-3 px-4 py-3 rounded-xl border
          ${v.bg} backdrop-blur-lg
          ${isExiting ? 'animate-slide-out-right' : 'animate-slide-in-right'}
        `}
      >
        <span className={`${v.text} text-sm font-bold mt-0.5`}>{v.icon}</span>
        <p className={`${v.text} text-sm flex-1`}>{message}</p>
        <button
          onClick={() => {
            setIsExiting(true);
            setTimeout(onClose, 300);
          }}
          className={`${v.text} opacity-60 hover:opacity-100 text-sm font-bold shrink-0`}
        >
          ×
        </button>
      </div>
    </div>
  );
}
