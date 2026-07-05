'use client';
import { useCallback, useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import {
  applyScene, FLOWS_SOURCE, BUBBLES_SOURCE, FLOWS_HIT_LAYER, type MapLike,
} from '../lib/scene';
import { placeLabels, largestRing, labelSpot } from '../lib/labels';
import { STATE_CENTROIDS } from '../lib/stateCentroids';
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

interface StateLabel {
  state: string;
  origin: [number, number];
  amount: number;
  el: HTMLDivElement;
}

interface District {
  spot: [number, number]; // pole of inaccessibility, lng/lat
  r: number; // inscribed radius, degrees
  ratio: number; // rendered text width per 1px of font-size
  el: HTMLDivElement;
}

export function MapView({ scene }: { scene: Scene | null }) {
  const container = useRef<HTMLDivElement>(null);
  const overlay = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);
  const ready = useRef(false);
  const hubRef = useRef<[number, number] | null>(null);
  const labelsRef = useRef<StateLabel[]>([]);
  const districtRef = useRef<District | null>(null);
  const tipRef = useRef<{
    showTip: (
      state: string | undefined,
      total: string | number | undefined,
      count: number | undefined,
      lngLat: maplibregl.LngLatLike,
    ) => void;
    hideTip: () => void;
  } | null>(null);

  // Reposition every overlay element against the current camera. Runs on every
  // map move so labels track the viewport and the watermark rescales.
  const placeAll = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;
    const cv = map.getCanvas();
    const W = cv.clientWidth;
    const H = cv.clientHeight;

    const hub = hubRef.current;
    const labels = labelsRef.current;
    if (hub && labels.length) {
      const hubPt = map.project(hub);
      const placements = placeLabels(
        labels.map((l) => ({ state: l.state, origin: l.origin, amount: l.amount })),
        hubPt,
        hub,
        (ll: [number, number]) => map.project(ll),
        W,
        H,
      );
      const by = new Map(placements.map((p) => [p.state, p]));
      for (const l of labels) {
        const p = by.get(l.state);
        if (p?.visible) {
          l.el.style.transform = `translate(${p.x}px, ${p.y}px) translate(-50%, -50%)`;
          l.el.style.opacity = '1';
        } else {
          l.el.style.opacity = '0';
        }
      }
    }

    const d = districtRef.current;
    if (d) {
      const c = map.project(d.spot);
      const edge = map.project([d.spot[0], d.spot[1] + d.r]);
      const rpx = Math.hypot(edge.x - c.x, edge.y - c.y);
      // Fit the text WIDTH inside the inscribed diameter (with margin) so it
      // never touches the district border.
      const targetW = 2 * rpx * 0.62;
      const size = Math.max(14, Math.min(targetW / d.ratio, 300));
      d.el.style.transform = `translate(${c.x}px, ${c.y}px) translate(-50%, -50%)`;
      d.el.style.fontSize = `${size}px`;
      d.el.style.opacity = rpx > 26 ? '1' : '0'; // hide when the district is tiny on screen
    }
  }, []);

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
      placeAll();
    });
    map.on('error', (e) => console.error('maplibre', e?.error ?? e));
    map.on('move', placeAll);

    // Shared tooltip + highlight, driven by both the map layers and the HTML
    // state labels (the natural place a person points).
    const popup = new maplibregl.Popup({
      closeButton: false,
      closeOnClick: false,
      className: 'otm-popup',
    });
    let hovered: string | null = null;
    const setHover = (state: string | null) => {
      if (hovered === state) return;
      for (const src of [FLOWS_SOURCE, BUBBLES_SOURCE]) {
        if (hovered) map.setFeatureState({ source: src, id: hovered }, { hover: false });
        if (state) map.setFeatureState({ source: src, id: state }, { hover: true });
      }
      hovered = state;
    };
    const showTip = (
      state: string | undefined,
      total: string | number | undefined,
      count: number | undefined,
      lngLat: maplibregl.LngLatLike,
    ) => {
      map.getCanvas().style.cursor = 'pointer';
      setHover(state ?? null);
      const amt = Number(total ?? 0).toLocaleString('en-US', { maximumFractionDigits: 0 });
      const donors = count ? ` &middot; ${count} donor${count === 1 ? '' : 's'}` : '';
      popup.setLngLat(lngLat).setHTML(`<b>${state}</b> &middot; $${amt}${donors}`).addTo(map);
    };
    const hideTip = () => {
      map.getCanvas().style.cursor = '';
      setHover(null);
      popup.remove();
    };
    tipRef.current = { showTip, hideTip };
    const show = (e: maplibregl.MapLayerMouseEvent) => {
      const f = e.features?.[0];
      if (!f) return;
      const p = f.properties as { state?: string; total?: string; count?: number };
      showTip(p.state, p.total, p.count, e.lngLat);
    };
    for (const layer of [BUBBLES_SOURCE, FLOWS_HIT_LAYER]) {
      map.on('mousemove', layer, show);
      map.on('mouseleave', layer, hideTip);
      map.on('click', layer, show); // tap support on touch devices
    }

    const ro = new ResizeObserver(() => {
      map.resize();
      placeAll();
    });
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
  }, [placeAll]);

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

      // Rebuild the state-label overlay for this scene.
      const cont = overlay.current;
      if (cont) {
        for (const l of labelsRef.current) l.el.remove();
        labelsRef.current = [];
        const home = scene.highlight.state.toUpperCase();
        for (const f of scene.flows) {
          const st = f.state.toUpperCase();
          const origin = STATE_CENTROIDS[st];
          if (!origin) continue;
          const lab = document.createElement('div');
          lab.className = `otm-label ${st === home ? 'is-in' : 'is-out'}`;
          lab.textContent = st;
          const total = f.total;
          const count = f.count;
          lab.addEventListener('mouseenter', () => {
            const tip = tipRef.current;
            if (!tip) return;
            const r = lab.getBoundingClientRect();
            const cr = map.getContainer().getBoundingClientRect();
            const lngLat = map.unproject([
              r.left + r.width / 2 - cr.left,
              r.top + r.height / 2 - cr.top,
            ]);
            tip.showTip(st, total, count, lngLat);
          });
          lab.addEventListener('mouseleave', () => tipRef.current?.hideTip());
          cont.appendChild(lab);
          labelsRef.current.push({ state: st, origin, amount: parseFloat(f.total) || 0, el: lab });
        }
      }
      hubRef.current = center;

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

          // District-code watermark, placed in the largest open area. A finer
          // grid gives a better-centered pole of inaccessibility.
          const spot = labelSpot(largestRing(feature.geometry), 90);
          if (overlay.current) {
            let el = districtRef.current?.el;
            if (!el) {
              el = document.createElement('div');
              el.className = 'otm-district-code';
              overlay.current.appendChild(el);
            }
            el.textContent = key.toUpperCase();
            // Measure text width once at a reference size; ratio lets placeAll
            // size the watermark to fit without a reflow every frame.
            el.style.fontSize = '100px';
            const ratio = el.offsetWidth / 100 || 3;
            districtRef.current = { spot: [spot.x, spot.y], r: spot.r, ratio, el };
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
      placeAll();
    };

    if (ready.current) run();
    else map.once('load', run);
  }, [scene, placeAll]);

  return (
    <div ref={container} className="map">
      <div ref={overlay} className="otm-overlay" />
    </div>
  );
}
