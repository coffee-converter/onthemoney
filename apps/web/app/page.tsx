'use client';
import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { Chat } from '../components/Chat';
import { Roster } from '../components/Roster';
import { fetchRoster, fetchCandidateScene } from '../lib/api';
import type { Scene, Candidate, RosterCandidate } from '../lib/types';

const MapView = dynamic(
  () => import('../components/MapView').then((m) => m.MapView),
  { ssr: false, loading: () => <div className="map map-loading">Loading map</div> },
);

export default function Home() {
  const [scene, setScene] = useState<Scene | null>(null);
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [roster, setRoster] = useState<RosterCandidate[]>([]);

  const districtKey = scene?.highlight
    ? `${scene.highlight.state}-${scene.highlight.district}`
    : '';

  // Load the roster of every candidate in the district when the district changes.
  useEffect(() => {
    if (!districtKey) {
      // overlay / custom-map scenes have no single district
      setRoster([]);
      setCandidate(null);
      return;
    }
    const [state, district] = districtKey.split('-');
    let cancelled = false;
    fetchRoster(state, district)
      .then((r) => !cancelled && setRoster(r))
      .catch(() => !cancelled && setRoster([]));
    return () => {
      cancelled = true;
    };
  }, [districtKey]);

  async function pickCandidate(c: RosterCandidate) {
    if (!scene?.highlight) return;
    const { state, district } = scene.highlight;
    try {
      const res = await fetchCandidateScene(c.cand_id, state, district);
      setCandidate({
        cand_id: c.cand_id,
        name: c.name,
        party: c.party,
        district: `${state}-${district}`,
        receipts: res.receipts,
        individualTotal: res.individual_total,
      });
      if (res.scene) setScene(res.scene);
    } catch {
      // leave the current view in place on failure
    }
  }

  return (
    <main className="layout">
      <section className="map-pane">
        <MapView scene={scene} candidate={candidate} />
        <Roster
          candidates={roster}
          activeCandId={candidate?.cand_id}
          district={districtKey}
          onPick={pickCandidate}
        />
        {scene && (
          <div className="map-legend">
            <span>
              <i className="in" />
              in-state money
            </span>
            <span>
              <i className="out" />
              out-of-state money
            </span>
          </div>
        )}
      </section>
      <aside className="rail">
        <Chat onScene={setScene} onCandidate={setCandidate} onReset={() => setRoster([])} />
      </aside>
    </main>
  );
}
