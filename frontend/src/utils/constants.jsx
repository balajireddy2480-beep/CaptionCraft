export const STYLES = [
  {
    id: 'formal',
    label: 'Formal',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4">
        <rect x="4" y="4" width="16" height="16" rx="2" />
      </svg>
    ),
    color: 'sage',
    bgClass: 'bg-style-formal/15',
    borderClass: 'border-style-formal',
    textClass: 'text-style-formal',
    dotClass: 'bg-style-formal',
    description: 'Professional & objective',
  },
  {
    id: 'sarcastic',
    label: 'Sarcastic',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4">
        <circle cx="12" cy="12" r="8" />
        <line x1="5" y1="19" x2="19" y2="5" />
      </svg>
    ),
    color: 'gold',
    bgClass: 'bg-style-sarcastic/15',
    borderClass: 'border-style-sarcastic',
    textClass: 'text-style-sarcastic',
    dotClass: 'bg-style-sarcastic',
    description: 'Dry wit & irony',
  },
  {
    id: 'humorous_tech',
    label: 'Tech Humor',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4">
        <polyline points="9,6 6,12 9,18" />
        <polyline points="15,6 18,12 15,18" />
      </svg>
    ),
    color: 'red',
    bgClass: 'bg-style-tech/15',
    borderClass: 'border-style-tech',
    textClass: 'text-style-tech',
    dotClass: 'bg-style-tech',
    description: 'Geeky & jargon-filled',
  },
  {
    id: 'humorous_non_tech',
    label: 'Non-Tech',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4">
        <polygon points="12,4 20,12 12,20 4,12" />
      </svg>
    ),
    color: 'darkred',
    bgClass: 'bg-style-nontech/15',
    borderClass: 'border-style-nontech',
    textClass: 'text-style-nontech',
    dotClass: 'bg-style-nontech',
    description: 'Relatable & punny',
  },
];

export const MAX_FILE_SIZE = 25 * 1024 * 1024;
export const MIN_DURATION = 5;
export const MAX_DURATION = 180;

export const ALLOWED_TYPES = [
  'video/mp4',
  'video/quicktime',
  'video/webm',
  'video/x-msvideo',
  'video/x-matroska',
];

export const ALLOWED_EXTENSIONS = ['.mp4', '.mov', '.avi', '.webm', '.mkv'];
