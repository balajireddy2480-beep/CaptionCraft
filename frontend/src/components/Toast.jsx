import { useEffect, useState } from 'react';

const VARIANTS = {
  error: {
    bg: 'bg-accent-copper/15 border-accent-copper/30',
    text: 'text-accent-copper',
  },
  success: {
    bg: 'bg-accent-sage/15 border-accent-sage/30',
    text: 'text-accent-sage',
  },
  warning: {
    bg: 'bg-accent-gold/15 border-accent-gold/30',
    text: 'text-accent-gold',
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

  const iconMap = {
    error: (
      <svg className="w-4 h-4 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
      </svg>
    ),
    success: (
      <svg className="w-4 h-4 shrink-0 mt-0.5 animate-scale-check" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
      </svg>
    ),
    warning: (
      <svg className="w-4 h-4 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
      </svg>
    ),
  };

  return (
    <div className="fixed top-6 right-6 z-50 max-w-sm">
      <div
        className={`
          flex items-start gap-3 px-4 py-3 rounded-xl border shadow-xl shadow-black/20
          ${v.bg} backdrop-blur-xl
          ${isExiting ? 'animate-slide-out-right' : 'animate-slide-in-right'}
        `}
      >
        {iconMap[variant] || iconMap.error}
        <p className={`${v.text} text-sm flex-1 leading-relaxed`}>{message}</p>
        <button
          onClick={() => {
            setIsExiting(true);
            setTimeout(onClose, 300);
          }}
          className={`${v.text} opacity-50 hover:opacity-100 shrink-0 transition-opacity`}
          aria-label="Dismiss notification"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}
