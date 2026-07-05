'use client';
import { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { applyScene, FLOWS_SOURCE, type MapLike } from '../lib/scene';
import type { Scene } from '../lib/types';

// CARTO dark basemap (free, no API key). A muted dark canvas so the money
// flows and district glow on top.
const DARK_STYLE = {
  version: 8 as const,
  sources: {
    carto: {
      type: 'raster' as const,
      tiles: [
        'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
        'https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
        'https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
        'https://d.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
      ],
      tileSize: 256,
      attribution: '(c) OpenStreetMap (c) CARTO',
    },
  },
  layers: [{ id: 'carto', type: 'raster' as const, source: 'carto' }],
};

type Ring = [number, number][];

function boundsOf(geom: { type: string; coordinates: unknown }): maplibregl.LngLatBoundsLike {
  const rings: Ring[] =
    geom.type === 'MultiPolygon'
      ? (geom.coordinates as Ring[][]).flat()
      : (geom.coordinates as Ring[]);
  let minX = 180, minY = 90, maxX = -180, maxY = -90;
  for (const ring of rings)
    for (const [x, y] of ring) {
      if (x < minX) minX = x;
      if (y < minY) minY = y;
      if (x > maxX) maxX = x;
      if (y > maxY) maxY = y;
    }
  return [[minX, minY], [maxX, maxY]];
}

export function MapView({ scene }: { scene: Scene | null }) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);
  const ready = useRef(false);

  useEffect(() => {
    if (!container.current || mapRef.current) return;
    const el = container.current;
    const map = new maplibregl.Map({
      container: el,
      style: DARK_STYLE as maplibregl.StyleSpecification,
      center: [-93, 40],
      zoom: 3.4,
    });
    map.on('load', () => {
      ready.current = true;
      map.resize();
    });
    map.on('error', (e) => console.error('maplibre', e?.error ?? e));
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

    const run = async () => {
      applyScene(map as unknown as MapLike, scene);

      const center: [number, number] = [scene.camera.lon, scene.camera.lat];
      if (!markerRef.current) {
        const el = document.createElement('div');
        el.className = 'otm-pulse';
        markerRef.current = new maplibregl.Marker({ element: el }).setLngLat(center).addTo(map);
      } else {
        markerRef.current.setLngLat(center);
      }

      let framed = false;
      try {
        const key = `${scene.highlight.state}-${scene.highlight.district}`;
        const res = await fetch(`/districts/${key}.json`);
        if (res.ok) {
          const feature = await res.json();
          const data = { type: 'FeatureCollection', features: [feature] };
          const existing = map.getSource('otm-district') as maplibregl.GeoJSONSource | undefined;
          if (existing) {
            existing.setData(data as never);
          } else {
            map.addSource('otm-district', { type: 'geojson', data: data as never });
            // draw the district under the flows
            map.addLayer(
              {
                id: 'otm-district-fill',
                type: 'fill',
                source: 'otm-district',
                paint: { 'fill-color': '#ffd24a', 'fill-opacity': 0.06 },
              },
              FLOWS_SOURCE,
            );
            map.addLayer(
              {
                id: 'otm-district-line',
                type: 'line',
                source: 'otm-district',
                paint: {
                  'line-color': '#ffd24a',
                  'line-width': 2.5,
                  'line-blur': 0.6,
                  'line-opacity': 0.9,
                },
              },
              FLOWS_SOURCE,
            );
          }
          map.fitBounds(boundsOf(feature.geometry), {
            padding: 70,
            duration: 1400,
            maxZoom: 11,
          });
          framed = true;
        }
      } catch (e) {
        console.error('district boundary', e);
      }
      if (!framed) {
        map.flyTo({ center, zoom: scene.camera.zoom, essential: true });
      }
    };

    if (ready.current) run();
    else map.once('load', run);
  }, [scene]);

  return <div ref={container} className="map" />;
}
