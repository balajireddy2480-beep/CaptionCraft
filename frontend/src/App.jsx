import { useState, useCallback } from 'react';
import Header from './components/Header';
import UploadZone from './components/UploadZone';
import VideoPreview from './components/VideoPreview';
import StyleSelector from './components/StyleSelector';
import FontSelector from './components/FontSelector';
import GenerateButton from './components/GenerateButton';
import Skeleton from './components/Skeleton';
import CaptionGrid from './components/CaptionGrid';
import ActionBar from './components/ActionBar';
import Footer from './components/Footer';
import Toast from './components/Toast';
import { useUpload } from './hooks/useUpload';
import { useCaptions } from './hooks/useCaptions';
import { STYLES } from './utils/constants';
import { BeamsBackground } from './components/ui/beams-background';

const HELP_STEPS = [
  { step: 1, title: 'Upload a video', desc: 'Drag & drop or browse for an MP4, MOV, WebM, AVI, or MKV file.' },
  { step: 2, title: 'Pick your styles', desc: 'Choose one or more caption tones — Formal, Sarcastic, Tech Humor, or Non-Tech.' },
  { step: 3, title: 'Generate captions', desc: 'AI analyzes your video and writes styled captions in seconds.' },
  { step: 4, title: 'Copy or download', desc: 'Copy individual captions or download the full set as JSON.' },
];

const DEFAULT_FONT = "'Inter', sans-serif";

export default function App() {
  const {
    file,
    preview,
    duration,
    error: uploadError,
    handleFileSelect,
    clearFile,
    setError: setUploadError,
  } = useUpload();

  const {
    captions,
    isLoading,
    uploadProgress,
    phase,
    error: captionError,
    generate,
    reset: resetCaptions,
  } = useCaptions();

  const [selectedStyles, setSelectedStyles] = useState(
    STYLES.map((s) => s.id)
  );

  const [selectedFont, setSelectedFont] = useState(DEFAULT_FONT);

  const [toast, setToast] = useState(null);
  const [showHelp, setShowHelp] = useState(false);

  const onFileSelect = useCallback((selectedFile) => {
    handleFileSelect(selectedFile);
    resetCaptions();
  }, [handleFileSelect, resetCaptions]);

  const onToggleStyle = useCallback((styleId) => {
    setSelectedStyles((prev) => {
      if (prev.includes(styleId)) {
        if (prev.length <= 1) return prev;
        return prev.filter((s) => s !== styleId);
      }
      return [...prev, styleId];
    });
  }, []);

  const onGenerate = useCallback(() => {
    if (!file || selectedStyles.length === 0) return;
    generate(file, selectedStyles);
  }, [file, selectedStyles, generate]);

  const onReset = useCallback(() => {
    clearFile();
    resetCaptions();
    setSelectedStyles(STYLES.map((s) => s.id));
    setSelectedFont(DEFAULT_FONT);
    setToast(null);
  }, [clearFile, resetCaptions]);

  const handleLogoClick = useCallback(() => {
    onReset();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [onReset]);

  const canGenerate = file && selectedStyles.length > 0 && !isLoading;
  const activeError = uploadError || captionError;

  return (
    <BeamsBackground intensity="subtle">
      <button
        onClick={handleLogoClick}
        className="fixed top-5 left-5 z-30 flex items-center gap-2 px-3 py-2 rounded-xl glass hover:glass-hover transition-all duration-200 cursor-pointer"
        aria-label="Reset to home"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5 text-accent-gold">
          <polygon points="5,3 19,12 5,21" />
        </svg>
      </button>

      <button
        onClick={() => setShowHelp(true)}
        className="fixed top-5 right-5 z-30 w-9 h-9 rounded-xl glass hover:glass-hover transition-all duration-200 cursor-pointer flex items-center justify-center"
        aria-label="How it works"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4.5 h-4.5 text-text-secondary">
          <circle cx="12" cy="12" r="10" />
          <path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
      </button>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 pt-10 pb-16">
        <Header />

        <main className="space-y-8">
          {!file ? (
            <UploadZone
              onFileSelect={onFileSelect}
              disabled={isLoading}
            />
          ) : (
            <VideoPreview
              file={file}
              preview={preview}
              duration={duration}
              onRemove={onReset}
            />
          )}

          {file && (
            <div className="relative z-20 animate-slide-up" style={{ animationDelay: '100ms' }}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <StyleSelector
                  selectedStyles={selectedStyles}
                  onToggle={onToggleStyle}
                  disabled={isLoading}
                />
                <FontSelector
                  selectedFont={selectedFont}
                  onFontChange={setSelectedFont}
                  disabled={isLoading}
                />
              </div>
            </div>
          )}

          {file && !captions && (
            <div className="relative z-10 animate-slide-up" style={{ animationDelay: '200ms' }}>
              <GenerateButton
                onClick={onGenerate}
                disabled={!canGenerate}
                isLoading={isLoading}
                phase={phase}
                uploadProgress={uploadProgress}
              />
            </div>
          )}

          {isLoading && phase === 'processing' && (
            <Skeleton count={selectedStyles.length} />
          )}

          {captions && (
            <>
              <CaptionGrid
                captions={captions}
                selectedStyles={selectedStyles}
                fontFamily={selectedFont}
              />
              <ActionBar
                captions={captions}
                onReset={onReset}
              />
            </>
          )}
        </main>

        <Footer />
      </div>

      {showHelp && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          onClick={() => setShowHelp(false)}
        >
          <div className="absolute inset-0 bg-bg-primary/80 backdrop-blur-md" />
          <div
            className="relative glass rounded-2xl max-w-md w-full p-6 animate-slide-up shadow-xl shadow-black/20"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold text-text-primary">How it works</h2>
              <button
                onClick={() => setShowHelp(false)}
                className="w-7 h-7 rounded-lg bg-white/[0.04] flex items-center justify-center hover:bg-white/[0.08] transition-colors cursor-pointer"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4 text-text-secondary">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            <div className="space-y-4">
              {HELP_STEPS.map((item) => (
                <div key={item.step} className="flex gap-3">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-accent-gold/20 flex items-center justify-center text-xs font-bold text-accent-gold">
                    {item.step}
                  </span>
                  <div>
                    <p className="text-text-primary text-sm font-medium">{item.title}</p>
                    <p className="text-text-muted text-xs mt-0.5">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeError && (
        <Toast
          message={activeError}
          variant="error"
          onClose={() => {
            setUploadError(null);
            if (captionError) resetCaptions();
          }}
        />
      )}

      {toast && (
        <Toast
          message={toast.message}
          variant={toast.variant}
          onClose={() => setToast(null)}
        />
      )}
    </BeamsBackground>
  );
}
