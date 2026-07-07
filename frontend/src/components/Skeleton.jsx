/**
 * Skeleton — Shimmer loading cards that match CaptionCard dimensions.
 */
export default function Skeleton({ count = 4 }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="rounded-2xl border border-border-subtle overflow-hidden animate-fade-in"
          style={{ animationDelay: `${i * 100}ms` }}
        >
          {/* Header skeleton */}
          <div className="px-5 py-3.5 border-b border-border-subtle">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg animate-shimmer" />
              <div className="w-24 h-4 rounded animate-shimmer" />
            </div>
          </div>

          {/* Body skeleton */}
          <div className="px-5 py-5 space-y-2.5">
            <div className="w-full h-4 rounded animate-shimmer" />
            <div className="w-4/5 h-4 rounded animate-shimmer" />
            <div className="w-3/5 h-4 rounded animate-shimmer" />
          </div>

          {/* Footer skeleton */}
          <div className="px-5 py-3 border-t border-border-subtle flex justify-between">
            <div className="w-16 h-5 rounded-full animate-shimmer" />
            <div className="w-12 h-5 rounded animate-shimmer" />
          </div>
        </div>
      ))}
    </div>
  );
}
