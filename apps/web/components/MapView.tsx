'use client';
import { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { applyScene, type MapLike } from '../lib/scene';
import type { Scene } from '../lib/types';

// A raster style renders map images directly (no vector-tile worker pipeline),
// which is the most reliable option across environments.
const RASTER_STYLE = {
  version: 8 as const,
  sources: {
    osm: {
      type: 'raster' as const,
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '(c) OpenStreetMap contributors',
    },
  },
  layers: [{ id: 'osm', type: 'raster' as const, source: 'osm' }],
};

export function MapView({ scene }: { scene: Scene | null }) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const ready = useRef(false);

  useEffect(() => {
    if (!container.current || mapRef.current) return;
    const el = container.current;
    const map = new maplibregl.Map({
      container: el,
      style: RASTER_STYLE as maplibregl.StyleSpecification,
      center: [-88, 42],
      zoom: 6,
    });
    map.on('load', () => {
      ready.current = true;
      map.resize();
    });
    map.on('error', (e) => console.error('maplibre', e?.error ?? e));

    // Keep the canvas matched to the pane, which is sized by flex.
    const ro = new ResizeObserver(() => map.resize());
    ro.observe(el);
    const t = setTimeout(() => map.resize(), 300);

    mapRef.current = map;
    return () => {
      clearTimeout(t);
      ro.disconnect();
      map.remove();
      mapRef.current = null;
      ready.current = false;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !scene) return;
    const run = () => applyScene(map as unknown as MapLike, scene);
    if (ready.current) run();
    else map.once('load', run);
  }, [scene]);

  return <div ref={container} className="map" />;
}
