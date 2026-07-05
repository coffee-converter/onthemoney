// Shared display formatting for FEC-sourced candidate data.

export function money(x: string | null | undefined): string | null {
  if (!x) return null;
  const n = parseFloat(x);
  if (!Number.isFinite(n)) return null;
  return `$${Math.round(n).toLocaleString()}`;
}

// Real party families -> clean badge; anything else (OTH, W, "18", TX...) drops.
const PARTY: Record<string, string> = {
  DEM: 'D', DFL: 'D', DNL: 'D',
  REP: 'R', GOP: 'R',
  IND: 'I', NPA: 'I', NON: 'I', NOP: 'I', NNE: 'I', NPP: 'I', UN: 'I', UND: 'I',
  LIB: 'L',
  GRE: 'G', GWP: 'G',
  CON: 'C',
};

export function partyLabel(code?: string): string | null {
  if (!code) return null;
  return PARTY[code.toUpperCase()] ?? null;
}

// Conventional party colors (informational, not partisan); gray when unknown.
const PARTY_COLOR: Record<string, string> = {
  D: '#4a90e2', // blue
  R: '#e2564a', // red
  G: '#43b26a', // green
  L: '#d99a2b', // amber (Libertarian)
  I: '#9b6dd6', // purple (independents)
  C: '#b0763a', // brown (Constitution)
};

export function partyColor(code?: string): string {
  const p = partyLabel(code);
  return (p && PARTY_COLOR[p]) || '#8b93a1';
}

const TITLES = new Set([
  'DR', 'MR', 'MRS', 'MS', 'MISS', 'HON', 'REV', 'PROF', 'SEN', 'REP', 'MAJ', 'COL', 'CAPT', 'LT', 'SGT',
]);
const SUFFIXES = new Set(['JR', 'SR', 'II', 'III', 'IV', 'V']);

function titleCase(s: string): string {
  return s.toLowerCase().replace(/\b[a-z]/g, (c) => c.toUpperCase());
}

// FEC stores "LAST, FIRST MIDDLE TITLE/SUFFIX". Render a clean "First Last[ Suffix]".
export function formatName(raw: string): string {
  const name = raw.trim();
  if (!name.includes(',')) return titleCase(name);
  const [last, rest = ''] = name.split(',').map((s) => s.trim());
  let first = '';
  const suffixes: string[] = [];
  for (const t of rest.split(/\s+/).filter(Boolean)) {
    const c = t.replace(/\./g, '').toUpperCase();
    if (SUFFIXES.has(c)) suffixes.push(c);
    else if (TITLES.has(c)) continue;
    else if (!first) first = t;
  }
  const suf = suffixes.length
    ? ' ' + suffixes.map((c) => (/^[IVX]+$/.test(c) ? c : `${titleCase(c)}.`)).join(' ')
    : '';
  return `${titleCase(first || rest)} ${titleCase(last)}${suf}`.trim();
}

export function initials(name: string): string {
  const n = name.trim();
  let first = '';
  let last = '';
  if (n.includes(',')) {
    const parts = n.split(',').map((s) => s.trim());
    last = parts[0] || '';
    first = parts[1] || '';
  } else {
    const p = n.split(/\s+/);
    first = p[0] || '';
    last = p[p.length - 1] || '';
  }
  return ((first[0] || '') + (last[0] || '')).toUpperCase() || '?';
}
