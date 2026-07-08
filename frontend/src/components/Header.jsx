export default function Header() {
  return (
    <header className="text-center pt-10 pb-6 px-4">
      <h1 className="font-[family-name:var(--font-display)] text-5xl md:text-6xl font-bold tracking-tight mb-3">
        <span className="bg-gradient-to-r from-accent-sage via-accent-gold to-accent-copper bg-clip-text text-transparent">
          CaptionCraft
        </span>
      </h1>
      <p className="text-text-secondary text-lg md:text-xl max-w-xl mx-auto leading-relaxed">
        Drop a video, pick your voice.
      </p>
    </header>
  );
}
