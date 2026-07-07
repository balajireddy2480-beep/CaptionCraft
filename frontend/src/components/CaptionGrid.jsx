/**
 * CaptionGrid — Responsive grid of CaptionCards.
 */
import CaptionCard from './CaptionCard';

export default function CaptionGrid({ captions, selectedStyles }) {
  if (!captions) return null;

  return (
    <div className="space-y-5">
      {/* Video summary */}
      {captions.video_summary && (
        <div className="glass rounded-xl px-5 py-4 animate-slide-up">
          <p className="text-text-muted text-xs font-medium uppercase tracking-wider mb-1.5">
            What the AI saw
          </p>
          <p className="text-text-secondary text-sm leading-relaxed">
            {captions.video_summary}
          </p>
        </div>
      )}

      {/* Caption cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {selectedStyles.map((styleId, index) => {
          const caption = captions[styleId];
          if (!caption) return null;

          return (
            <CaptionCard
              key={styleId}
              styleId={styleId}
              caption={caption}
              delay={index * 120}
            />
          );
        })}
      </div>

      {/* Processing time */}
      {captions.processing_time_seconds > 0 && (
        <p className="text-text-muted text-xs text-center animate-fade-in">
          Generated in {captions.processing_time_seconds.toFixed(1)}s using{' '}
          <span className="text-text-secondary">{captions.model_used?.split('/').pop()}</span>
        </p>
      )}
    </div>
  );
}
