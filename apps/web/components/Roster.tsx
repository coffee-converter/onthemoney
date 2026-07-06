import type { RosterCandidate } from '../lib/types';
import { formatName, partyLabel, partyColor, money } from '../lib/format';

// Surname only, title-cased, for a compact pill (FEC names are "LAST, FIRST").
function surname(fecName: string): string {
  const last = (fecName.split(',')[0] || '').trim();
  return last.toLowerCase().replace(/(^|[\s-])(\w)/g, (_, sep, ch) => sep + ch.toUpperCase());
}

// A compact candidate switcher pinned over the map: one pill per candidate in
// the district, the active one filled with its party color. Clicking a pill
// swaps the map to that candidate's funding view.
export function Roster({
  candidates,
  activeCandId,
  onPick,
}: {
  candidates: RosterCandidate[];
  activeCandId?: string;
  onPick: (c: RosterCandidate) => void;
}) {
  if (candidates.length < 2) return null; // nothing to switch between

  return (
    <div className="switcher">
      <div className="switcher-label">Candidates in this district</div>
      <div className="switcher-pills">
        {candidates.map((c) => {
          const active = c.cand_id === activeCandId;
          const color = partyColor(c.party);
          const p = partyLabel(c.party);
          return (
            <button
              key={c.cand_id}
              type="button"
              className={active ? 'pill active' : 'pill'}
              style={active ? { background: color, borderColor: color } : { borderColor: color }}
              onClick={() => onPick(c)}
              title={`${formatName(c.name)}${p ? ` (${p})` : ''} · ${money(c.itemized)}`}
            >
              <span className="pill-dot" style={{ background: color }} />
              <span className="pill-name">{surname(c.name)}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
