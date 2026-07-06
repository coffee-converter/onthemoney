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
  district,
  onPick,
}: {
  candidates: RosterCandidate[];
  activeCandId?: string;
  district?: string;
  onPick: (c: RosterCandidate) => void;
}) {
  if (candidates.length < 2) return null; // nothing to switch between

  // The default district view (emit_scene) shows the leader, so when nothing
  // specific is selected, mark the leader (top of the ranked roster) active.
  const activeId = candidates.some((c) => c.cand_id === activeCandId)
    ? activeCandId
    : candidates[0]?.cand_id;

  return (
    <div className="switcher">
      <div className="switcher-label">Candidates in {district || 'this district'}</div>
      <div className="switcher-pills">
        {candidates.map((c) => {
          const active = c.cand_id === activeId;
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
              {p && (
                <span className="pill-letter" style={{ color }}>
                  {p}
                </span>
              )}
              <span className="pill-name">{surname(c.name)}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
