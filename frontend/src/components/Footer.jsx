const LINKS = [
  { label: 'Privacy Policy', href: '#' },
  { label: 'Safety & Security', href: '#' },
  { label: 'Captions on Web Terms', href: '#' },
  { label: 'Captions on Web User Terms', href: '#' },
  { label: 'Captions Terms', href: '#' },
];

export default function Footer() {
  return (
    <footer className="border-t border-border-subtle mt-20 pt-6 pb-8">
      <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center sm:gap-6">
        <p className="text-text-muted text-xs leading-relaxed text-center sm:text-left">
          &copy; 2026 NOCAP, Inc. d/b/a Captions. All rights reserved.
        </p>
        <nav className="flex flex-wrap justify-center gap-x-4 gap-y-1" aria-label="Footer links">
          {LINKS.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="text-text-muted text-xs hover:text-accent-copper transition-colors duration-200"
            >
              {link.label}
            </a>
          ))}
        </nav>
      </div>
    </footer>
  );
}
