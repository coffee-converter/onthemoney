import type { Citation } from '../lib/types';

export function Citations({ items }: { items: Citation[] }) {
  if (!items.length) return null;
  return (
    <ul className="citations">
      {items.map((c) => (
        <li key={c.url}>
          <a href={c.url} target="_blank" rel="noreferrer">
            {c.label}
          </a>
        </li>
      ))}
    </ul>
  );
}
