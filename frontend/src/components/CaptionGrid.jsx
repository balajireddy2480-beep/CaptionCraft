import CaptionCard from './CaptionCard';

export default function CaptionGrid({ captions, selectedStyles, fontFamily }) {
  if (!captions) return null;

  const processingTime = Number(captions.processing_time_seconds);
  const hasProcessingTime = Number.isFinite(processingTime) && processingTime > 0;

  return (
    <div className="space-y-5">
      {captions.video_summary && (
        <div className="glass rounded-xl px-5 py-4 animate-slide-up shadow-lg shadow-black/5">
          <p className="text-text-muted text-xs font-medium uppercase tracking-wider mb-1.5">
            What the AI saw
          </p>
          <p className="text-text-secondary text-sm leading-relaxed">
            {captions.video_summary}
          </p>
        </div>
      )}

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
              fontFamily={fontFamily}
            />
          );
        })}
      </div>

      {hasProcessingTime && (
        <p className="text-text-muted text-xs text-center animate-fade-in">
          Generated in {processingTime.toFixed(1)}s using{' '}
          <span className="text-text-secondary">{captions.model_used?.split('/').pop()}</span>
        </p>
      )}
    </div>
  );
}
