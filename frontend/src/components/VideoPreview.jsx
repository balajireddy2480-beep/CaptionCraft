import { formatFileSize, formatDuration } from '../utils/helpers';

export default function VideoPreview({ file, preview, duration, onRemove }) {
  return (
    <div className="glass rounded-2xl overflow-hidden animate-slide-up shadow-lg shadow-black/10">
      <div className="relative bg-black/50">
        <video
          src={preview}
          controls
          className="w-full max-h-[400px] object-contain"
          preload="metadata"
        />
      </div>

      <div className="flex items-center justify-between px-5 py-3.5">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-9 h-9 rounded-lg bg-accent-sage/15 flex items-center justify-center shrink-0">
            <svg className="w-4.5 h-4.5 text-accent-sage" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round"
                d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z"
              />
            </svg>
          </div>
          <div className="min-w-0">
            <p className="text-text-primary text-sm font-medium truncate">{file.name}</p>
            <p className="text-text-muted text-xs">
              {formatFileSize(file.size)}
              {duration > 0 && ` \u2022 ${formatDuration(duration)}`}
            </p>
          </div>
        </div>

        <button
          onClick={onRemove}
          className="shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium
                     text-text-secondary bg-white/[0.04] border border-border-subtle
                     hover:bg-accent-copper/15 hover:text-accent-copper hover:border-accent-copper/30
                     transition-all duration-200"
        >
          Remove
        </button>
      </div>
    </div>
  );
}
