import { useState, useCallback } from 'react';
import { STYLES } from '../utils/constants';
import { countWords } from '../utils/helpers';

export default function CaptionCard({ styleId, caption, delay = 0 }) {
  const [copied, setCopied] = useState(false);

  const style = STYLES.find((s) => s.id === styleId);
  if (!style) return null;

  const wordCount = countWords(caption);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(caption);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = caption;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [caption]);

  return (
    <div
      className="glass rounded-2xl overflow-hidden animate-slide-up hover:glass-hover transition-all duration-300 group"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className={`px-5 py-3.5 border-b border-border-subtle flex items-center gap-3`}>
        <div className={`w-8 h-8 rounded-lg ${style.bgClass} flex items-center justify-center`}>
          <span className="text-current">{style.icon}</span>
        </div>
        <div>
          <p className={`text-sm font-semibold ${style.textClass}`}>{style.label}</p>
          <p className="text-text-muted text-[11px]">{style.description}</p>
        </div>
      </div>

      <div className="px-5 py-5">
        <p className="text-text-primary text-[15px] leading-relaxed">
          {caption}
        </p>
      </div>

      <div className="px-5 py-3 border-t border-border-subtle flex items-center justify-between">
        <span className="text-[11px] font-medium text-text-muted bg-white/5 px-2.5 py-1 rounded-full">
          {wordCount} words
        </span>
        <button
          onClick={handleCopy}
          className={`
            text-xs font-medium px-3 py-1.5 rounded-lg
            transition-all duration-200
            ${copied
              ? 'bg-success/15 text-success'
              : 'text-text-secondary hover:text-text-primary hover:bg-white/5'
            }
          `}
        >
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
    </div>
  );
}
