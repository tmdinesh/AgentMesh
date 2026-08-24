/**
 * Date and Timestamp Utilities
 * Correctly parses UTC datetimes stored by SQLite/backend and converts to local browser timezone.
 */

export function parseUtcDate(dateInput) {
  if (!dateInput) return null;
  if (dateInput instanceof Date) return dateInput;
  
  let str = String(dateInput).trim();
  // Replace space with 'T' if format is 'YYYY-MM-DD HH:mm:ss'
  if (str.includes(' ') && !str.includes('T')) {
    str = str.replace(' ', 'T');
  }
  // If missing timezone indicator, enforce UTC 'Z'
  if (!str.endsWith('Z') && !/\+\d{2}:?\d{2}$/.test(str) && !/-\d{2}:\d{2}$/.test(str)) {
    str = `${str}Z`;
  }
  
  const parsed = new Date(str);
  return isNaN(parsed.getTime()) ? new Date(dateInput) : parsed;
}

export function formatDateTime(dateInput) {
  const d = parseUtcDate(dateInput);
  if (!d || isNaN(d.getTime())) return '';
  return d.toLocaleString([], {
    month: 'numeric',
    day: 'numeric',
    year: '2-digit',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

export function formatTime(dateInput) {
  const d = parseUtcDate(dateInput);
  if (!d || isNaN(d.getTime())) return '';
  return d.toLocaleTimeString([], {
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  });
}
