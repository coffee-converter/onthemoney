'use client';
import { useState } from 'react';
import dynamic from 'next/dynamic';
import { Chat } from '../components/Chat';
import type { Scene } from '../lib/types';

const MapView = dynamic(
  () => import('../components/MapView').then((m) => m.MapView),
  { ssr: false, loading: () => <div className="map map-loading">Loading map</div> },
);

export default function Home() {
  const [scene, setScene] = useState<Scene | null>(null);
  return (
    <main className="layout">
      <section className="map-pane">
        <MapView scene={scene} />
      </section>
      <aside className="rail">
        <Chat onScene={setScene} />
      </aside>
    </main>
  );
}
