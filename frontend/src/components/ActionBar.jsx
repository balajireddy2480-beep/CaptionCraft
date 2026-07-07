/**
 * ActionBar — Download JSON and Try Another buttons.
 */
import { useCallback } from 'react';

export default function ActionBar({ captions, onReset }) {

  const handleDownload = useCallback(() => {
    if (!captions) return;

    const exportData = {
      formal: captions.formal || null,
      sarcastic: captions.sarcastic || null,
      humorous_tech: captions.humorous_tech || null,
      humorous_non_tech: captions.humorous_non_tech || null,
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `captions_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [captions]);

  return (
    <div className="flex flex-col sm:flex-row gap-3 animate-slide-up" style={{ animationDelay: '500ms' }}>
      {/* Download JSON */}
      <button
        onClick={handleDownload}
        className="flex-1 flex items-center justify-center gap-2 px-5 py-3 rounded-xl
                   text-sm font-medium bg-white/5 border border-border-subtle
                   text-text-secondary hover:text-text-primary hover:bg-white/8
                   hover:border-border-hover transition-all duration-200"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"
          />
        </svg>
        Download JSON
      </button>

      {/* Try Another */}
      <button
        onClick={onReset}
        className="flex-1 flex items-center justify-center gap-2 px-5 py-3 rounded-xl
                   text-sm font-medium border border-accent-gold/30
                    text-accent-gold hover:bg-accent-gold/10
                   transition-all duration-200"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182"
          />
        </svg>
        Try Another Video
      </button>
    </div>
  );
}
