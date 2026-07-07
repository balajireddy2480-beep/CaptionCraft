/**
 * GenerateButton — CTA button with loading state and upload progress.
 */
export default function GenerateButton({
  onClick,
  disabled,
  isLoading,
  phase,
  uploadProgress,
}) {
  const getButtonText = () => {
    switch (phase) {
      case 'uploading':
        return `Uploading... ${uploadProgress}%`;
      case 'processing':
        return 'Analyzing video...';
      default:
        return 'Generate Captions';
    }
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled || isLoading}
      className={`
        relative w-full py-4 px-6 rounded-xl text-base font-semibold
        transition-all duration-300 ease-out overflow-hidden
        ${disabled || isLoading
          ? 'bg-white/5 text-text-muted cursor-not-allowed border border-border-subtle'
          : 'bg-gradient-to-r from-accent-sage to-accent-gold text-white shadow-lg shadow-accent-gold/20 hover:shadow-xl hover:shadow-accent-gold/30 hover:scale-[1.01] active:scale-[0.99]'
        }
      `}
    >
      {/* Upload progress bar overlay */}
      {phase === 'uploading' && (
        <div
          className="absolute inset-y-0 left-0 bg-white/10 transition-all duration-300 ease-out"
          style={{ width: `${uploadProgress}%` }}
        />
      )}

      <span className="relative z-10 flex items-center justify-center gap-2.5">
        {isLoading && (
          <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        )}
        {getButtonText()}
      </span>
    </button>
  );
}
