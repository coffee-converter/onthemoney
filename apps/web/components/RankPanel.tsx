import type { Scene } from '../lib/types';

// FEC names are "LAST, FIRST"; show a compact title-cased surname.
function surname(fec: string): string {
  const last = (fec.split(',')[0] || '').trim();
  return last.toLowerCase().replace(/(^|[\s-])(\w)/g, (_, sep, ch) => sep + ch.toUpperCase());
}

// A compact ranked list for a multi-district ranking map (rank_districts /
// map_districts), so the pane lists the seats and totals instead of leaving the
// user to read shaded shapes. Only a ranking map labels every district with its
// total, so a plain choropleth (map_nation) leaves this hidden.
export function RankPanel({ scene }: { scene: Scene | null }) {
  const regions = scene?.overlays?.find((o) => o.type === 'regions')?.regions;
  if (!regions || regions.length < 2 || !regions.every((r) => r.label)) return null;
  return (
    <div className="rankpanel">
      <div className="rankpanel-title">{scene?.title || 'Ranked districts'}</div>
      <ol className="rankpanel-list">
        {regions.map((r) => {
          const name = r.tooltip?.[1];
          return (
            <li key={r.place}>
              <span className="rp-place">{r.place}</span>
              {name ? <span className="rp-name">{surname(name)}</span> : null}
              <span className="rp-val">{r.label}</span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
