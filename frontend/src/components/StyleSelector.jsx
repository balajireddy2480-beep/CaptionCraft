import { STYLES } from '../utils/constants';

export default function StyleSelector({ selectedStyles, onToggle, disabled }) {
  return (
    <div className="space-y-3">
      <p className="font-[family-name:var(--font-geist-pixel)] text-text-secondary text-sm font-medium tracking-wider uppercase">Select caption styles</p>
      <div className="flex flex-wrap gap-3">
        {STYLES.map((style) => {
          const isActive = selectedStyles.includes(style.id);

          return (
            <button
              key={style.id}
              onClick={() => onToggle(style.id)}
              disabled={disabled}
              className={`
                relative flex items-center gap-2.5 px-4 py-2.5 rounded-full
                text-sm font-medium transition-all duration-250 ease-out
                border select-none font-[family-name:var(--font-geist-pixel)]
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                ${isActive
                  ? `${style.bgClass} ${style.borderClass} ${style.textClass} shadow-sm`
                  : 'bg-white/[0.03] border-border-subtle text-text-muted hover:bg-white/[0.06] hover:border-border-hover hover:text-text-secondary'
                }
              `}
              aria-pressed={isActive}
            >
              <span className="flex items-center justify-center w-4 h-4">
                {style.icon}
              </span>
              <span>{style.label}</span>

              {isActive && (
                <span
                  className={`w-2 h-2 rounded-full ${style.dotClass} animate-fade-in`}
                  style={{ boxShadow: '0 0 6px 1px rgba(255,255,255,0.25)' }}
                />
              )}
            </button>
          );
        })}
      </div>
      {selectedStyles.length === 0 && (
        <p className="text-error text-xs animate-fade-in">Select at least one style.</p>
      )}
    </div>
  );
}
