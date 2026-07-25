// Small formatting helpers shared across pages.

export function relativeTime(iso) {
  if (!iso) return '';
  // The API returns naive UTC timestamps ("2026-07-24 17:30:16"); treat them as UTC.
  const then = new Date(iso.replace(' ', 'T') + 'Z').getTime();
  if (Number.isNaN(then)) return '';
  const diff = Date.now() - then;
  const mins = Math.round(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(then).toLocaleDateString();
}

// Strip markdown so the text-to-speech voice doesn't read "asterisk asterisk".
export function speakableText(text) {
  if (!text) return '';
  return text
    .replace(/```[\s\S]*?```/g, ' code block ')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/[#*_>~]+/g, '')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/https?:\/\/\S+/g, 'a link')
    .replace(/\s+/g, ' ')
    .trim();
}
