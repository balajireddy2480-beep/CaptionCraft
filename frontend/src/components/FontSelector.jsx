import { useState, useRef, useCallback, useEffect } from 'react';

const FONTS = [
  { name: 'Inter', family: "'Inter', sans-serif" },
  { name: 'Poppins', family: "'Poppins', sans-serif" },
  { name: 'DM Sans', family: "'DM Sans', sans-serif" },
  { name: 'Space Grotesk', family: "'Space Grotesk', sans-serif" },
  { name: 'Manrope', family: "'Manrope', sans-serif" },
  { name: 'Outfit', family: "'Outfit', sans-serif" },
  { name: 'Plus Jakarta Sans', family: "'Plus Jakarta Sans', sans-serif" },
  { name: 'Urbanist', family: "'Urbanist', sans-serif" },
  { name: 'Playfair Display', family: "'Playfair Display', serif" },
  { name: 'Merriweather', family: "'Merriweather', serif" },
];

const PREVIEW_TEXT = 'A caption in this voice reads like this — crisp, clear, and unmistakably yours.';

export default function FontSelector({ selectedFont, onFontChange, disabled }) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const dropdownRef = useRef(null);
  const inputRef = useRef(null);

  const filtered = search
    ? FONTS.filter((f) => f.name.toLowerCase().includes(search.toLowerCase()))
    : FONTS;

  const selected = FONTS.find((f) => f.family === selectedFont) || FONTS[0];

  useEffect(() => {
    function handleClickOutside(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
        setSearch('');
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleToggle = useCallback(() => {
    if (!disabled) {
      setIsOpen((prev) => !prev);
      if (!isOpen) setSearch('');
    }
  }, [disabled, isOpen]);

  const handleSelect = useCallback((font) => {
    onFontChange(font.family);
    setIsOpen(false);
    setSearch('');
  }, [onFontChange]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Escape') {
      setIsOpen(false);
      setSearch('');
    }
  }, []);

  return (
    <div className="space-y-3" ref={dropdownRef}>
      <label className="flex items-center gap-2 text-text-secondary text-sm font-medium tracking-wide">
        <svg className="w-4 h-4 text-accent-gold" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="m9 9 10.5-3m0 6.553v3.75a2.25 2.25 0 0 1-1.632 2.163l-1.32.377a1.803 1.803 0 0 1-.99-.144l-3.6-1.32A2.25 2.25 0 0 1 10.5 15.78V12M9 9v3.75m0-3.75L9 3l10.5 3M9 12l10.5-3" />
        </svg>
        Caption Font
      </label>

      {/* Trigger button */}
      <button
        onClick={handleToggle}
        disabled={disabled}
        className="w-full flex items-center justify-between gap-2 px-4 py-3 rounded-xl glass hover:glass-hover transition-all duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label="Select caption font"
      >
        <span className="text-text-primary text-sm" style={{ fontFamily: selected.family }}>
          {selected.name}
        </span>
        <svg
          className={`w-4 h-4 text-text-muted transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="relative animate-fade-in">
          <div className="absolute top-0 left-0 right-0 z-20 bg-black rounded-xl border border-border-hover shadow-xl shadow-black/40 overflow-hidden">
            {/* Search input */}
            <div className="px-3 py-2.5 border-b border-border-subtle">
              <input
                ref={inputRef}
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Search fonts..."
                className="w-full bg-transparent text-text-primary text-sm placeholder:text-text-muted outline-none"
                autoFocus
                aria-label="Search fonts"
              />
            </div>

            {/* Font list */}
            <div className="max-h-56 overflow-y-auto py-1" role="listbox" aria-label="Available fonts">
              {filtered.length === 0 ? (
                <p className="px-4 py-3 text-text-muted text-sm text-center">No fonts found</p>
              ) : (
                filtered.map((font) => {
                  const isActive = font.family === selectedFont;
                  return (
                    <button
                      key={font.name}
                      onClick={() => handleSelect(font)}
                      role="option"
                      aria-selected={isActive}
                      className={`w-full flex items-center justify-between px-4 py-2.5 text-sm transition-colors duration-150 cursor-pointer ${
                        isActive
                          ? 'bg-accent-gold/10 text-accent-gold'
                          : 'text-text-primary hover:bg-white/[0.06]'
                      }`}
                    >
                      <span style={{ fontFamily: font.family }}>{font.name}</span>
                      {isActive && (
                        <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                        </svg>
                      )}
                    </button>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}

      {/* Live preview */}
      {!isOpen && (
        <div className="rounded-xl bg-white/[0.02] border border-border-subtle px-4 py-3 min-h-[3rem] transition-all duration-200">
          <p
            className="text-text-primary text-base leading-relaxed"
            style={{ fontFamily: selectedFont }}
          >
            {PREVIEW_TEXT}
          </p>
        </div>
      )}
    </div>
  );
}
