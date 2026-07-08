import { useState, useRef, useCallback } from 'react';

export default function UploadZone({ onFileSelect, disabled }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef(null);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) setIsDragOver(true);
  }, [disabled]);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    if (disabled) return;
    const files = e.dataTransfer.files;
    if (files.length > 0) onFileSelect(files[0]);
  }, [onFileSelect, disabled]);

  const handleClick = useCallback(() => {
    if (!disabled && inputRef.current) inputRef.current.click();
  }, [disabled]);

  const handleInputChange = useCallback((e) => {
    const files = e.target.files;
    if (files.length > 0) onFileSelect(files[0]);
    e.target.value = '';
  }, [onFileSelect]);

  return (
    <div
      onClick={handleClick}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleClick(); }}
      className={`
        relative cursor-pointer rounded-2xl border-2 border-dashed p-12 md:p-16
        transition-all duration-300 ease-out text-center group
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        ${isDragOver
          ? 'border-accent-gold bg-accent-gold/[0.08] scale-[1.01] shadow-lg shadow-accent-gold/10'
          : 'border-border-subtle hover:border-border-hover hover:bg-white/[0.02]'
        }
      `}
    >
      <div className={`
        mx-auto mb-5 w-16 h-16 rounded-2xl flex items-center justify-center
        transition-all duration-300
        ${isDragOver
          ? 'bg-accent-gold/20 scale-110'
          : 'bg-white/[0.04] group-hover:bg-white/[0.06]'
        }
      `}>
        <svg
          className={`w-8 h-8 transition-colors duration-300 ${isDragOver ? 'text-accent-gold' : 'text-text-muted group-hover:text-text-secondary'}`}
          fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
          />
        </svg>
      </div>

      <p className="text-text-primary text-lg font-medium mb-1.5">
        {isDragOver ? 'Drop your video here' : 'Drag & drop your video'}
      </p>
      <p className="text-text-muted text-sm">
        or <span className="text-accent-gold underline underline-offset-2 decoration-accent-gold/40 hover:decoration-accent-gold/80 transition-all">browse files</span>
      </p>
      <p className="text-text-muted text-xs mt-3">
        MP4, MOV, WebM, AVI, MKV &bull; Max 25 MB
      </p>

      <input
        ref={inputRef}
        type="file"
        accept="video/*"
        onChange={handleInputChange}
        className="hidden"
        aria-label="Select video file"
      />
    </div>
  );
}
