import type { RosterCandidate } from '../lib/types';
import { formatName, partyLabel, money } from '../lib/format';

export function Roster({
  candidates,
  activeCandId,
  onPick,
}: {
  candidates: RosterCandidate[];
  activeCandId?: string;
  onPick: (c: RosterCandidate) => void;
}) {
  if (candidates.length < 2) return null; // nothing to compare
  const max = Math.max(...candidates.map((c) => parseFloat(c.itemized) || 0), 1);
  return (
    <div className="roster">
      <div className="roster-title">Candidates in this district</div>
      <ul>
        {candidates.map((c) => {
          const amt = parseFloat(c.itemized) || 0;
          const pct = Math.max(4, (amt / max) * 100);
          const active = c.cand_id === activeCandId;
          const p = partyLabel(c.party);
          return (
            <li key={c.cand_id}>
              <button
                type="button"
                className={active ? 'roster-row active' : 'roster-row'}
                onClick={() => onPick(c)}
              >
                <div className="roster-head">
                  <span className="roster-name">{formatName(c.name)}</span>
                  {p && <span className="roster-party">{p}</span>}
                  <span className="roster-amt">{money(c.itemized)}</span>
                </div>
                <div className="roster-bar">
                  <span style={{ width: `${pct}%` }} />
                </div>
              </button>
            </li>
          );
        })}
      </ul>
      <div className="roster-note">Ranked by itemized individual receipts.</div>
    </div>
  );
}
