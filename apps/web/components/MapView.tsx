'use client';
import { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { applyScene, type MapLike } from '../lib/scene';
import type { Scene } from '../lib/types';

const STYLE =
  process.env.NEXT_PUBLIC_MAP_STYLE || 'https://demotiles.maplibre.org/style.json';

export function MapView({ scene }: { scene: Scene | null }) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const ready = useRef(false);

  useEffect(() => {
    if (!container.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: container.current,
      style: STYLE,
      center: [-98, 39],
      zoom: 3,
    });
    map.on('load', () => {
      ready.current = true;
    });
    mapRef.current = map;
    return () => {
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
