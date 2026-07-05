'use client';
import { useCallback, useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import {
  applyScene, FLOWS_SOURCE, BUBBLES_SOURCE, FLOWS_HIT_LAYER, type MapLike,
} from '../lib/scene';
import { placeLabels, largestRing, labelSpot } from '../lib/labels';
import { STATE_CENTROIDS } from '../lib/stateCentroids';
import type { Scene, Candidate } from '../lib/types';

function money(x: string | null | undefined): string | null {
  if (!x) return null;
  const n = parseFloat(x);
  if (!Number.isFinite(n)) return null;
  return `$${Math.round(n).toLocaleString()}`;
}

const ESC: Record<string, string> = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' };
function esc(s: string): string {
  return s.replace(/[&<>"]/g, (c) => ESC[c]);
}

// Real party families -> clean badge; anything else (OTH, W, "18", TX...) is dropped.
const PARTY: Record<string, string> = {
  DEM: 'D', DFL: 'D', DNL: 'D',
  REP: 'R', GOP: 'R',
  IND: 'I', NPA: 'I', NON: 'I', NOP: 'I', NNE: 'I', NPP: 'I', UN: 'I', UND: 'I',
  LIB: 'L',
  GRE: 'G', GWP: 'G',
  CON: 'C',
};
function partyLabel(code?: string): string | null {
  if (!code) return null;
  return PARTY[code.toUpperCase()] ?? null;
}

const TITLES = new Set([
  'DR', 'MR', 'MRS', 'MS', 'MISS', 'HON', 'REV', 'PROF', 'SEN', 'REP', 'MAJ', 'COL', 'CAPT', 'LT', 'SGT',
]);
const SUFFIXES = new Set(['JR', 'SR', 'II', 'III', 'IV', 'V']);

function titleCase(s: string): string {
  return s.toLowerCase().replace(/\b[a-z]/g, (c) => c.toUpperCase());
}

// FEC stores "LAST, FIRST MIDDLE TITLE/SUFFIX". Render a clean "First Last[ Suffix]".
function formatName(raw: string): string {
  const name = raw.trim();
  if (!name.includes(',')) return titleCase(name);
  const [last, rest = ''] = name.split(',').map((s) => s.trim());
  let first = '';
  const suffixes: string[] = [];
  for (const t of rest.split(/\s+/).filter(Boolean)) {
    const c = t.replace(/\./g, '').toUpperCase();
    if (SUFFIXES.has(c)) suffixes.push(c);
    else if (TITLES.has(c)) continue;
    else if (!first) first = t; // first non-title token is the given name
    // middle names/initials dropped for a compact card
  }
  const suf = suffixes.length
    ? ' ' + suffixes.map((c) => (/^[IVX]+$/.test(c) ? c : `${titleCase(c)}.`)).join(' ')
    : '';
  return `${titleCase(first || rest)} ${titleCase(last)}${suf}`.trim();
}

// FEC names are "LAST, FIRST" - derive first+last initials.
function initials(name: string): string {
  const n = name.trim();
  let first = '';
  let last = '';
  if (n.includes(',')) {
    const parts = n.split(',').map((s) => s.trim());
    last = parts[0] || '';
    first = parts[1] || '';
  } else {
    const p = n.split(/\s+/);
    first = p[0] || '';
    last = p[p.length - 1] || '';
  }
  return ((first[0] || '') + (last[0] || '')).toUpperCase() || '?';
}

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

export function MapView({
  scene,
  candidate,
}: {
  scene: Scene | null;
  candidate: Candidate | null;
}) {
  const container = useRef<HTMLDivElement>(null);
  const cardRef = useRef<HTMLDivElement | null>(null);
  const overlay = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);
  const ready = useRef(false);
  const hubRef = useRef<[number, number] | null>(null);
  const labelsRef = useRef<StateLabel[]>([]);
  const flowOriginsRef = useRef<[number, number][]>([]);
  const districtRef = useRef<District | null>(null);
  const pulseRef = useRef<number | null>(null);
  const animRef = useRef<number | null>(null);
  const animTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const animatingRef = useRef(false);
  const loadingStartRef = useRef(0);
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
    if (animatingRef.current) {
      for (const l of labels) l.el.style.opacity = '0'; // hidden until beams finish
    } else if (hub && labels.length) {
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

    const card = cardRef.current;
    if (card && card.dataset.show === '1' && hubRef.current) {
      const dot = map.project(hubRef.current);
      const cw = card.offsetWidth || 200;
      const ch = card.offsetHeight || 60;
      const gap = 16;
      // Count beams per screen quadrant (right-down, left-down, right-up, left-up).
      const q = [0, 0, 0, 0];
      for (const o of flowOriginsRef.current) {
        const s = map.project(o);
        q[(s.x >= dot.x ? 0 : 1) + (s.y >= dot.y ? 0 : 2)]++;
      }
      // Which quadrants keep the whole card on screen.
      const fitR = dot.x + gap + cw <= W;
      const fitL = dot.x - gap - cw >= 0;
      const fitD = dot.y + gap + ch <= H;
      const fitU = dot.y - gap - ch >= 0;
      const fit = [fitR && fitD, fitL && fitD, fitR && fitU, fitL && fitU];
      // Emptiest quadrant that fits; if none fit, emptiest overall.
      let best = -1;
      for (let i = 0; i < 4; i++) if (fit[i] && (best < 0 || q[i] < q[best])) best = i;
      if (best < 0) {
        best = 0;
        for (let i = 1; i < 4; i++) if (q[i] < q[best]) best = i;
      }
      const hx = best % 2 === 0 ? 1 : -1;
      const vy = best < 2 ? 1 : -1;
      const ax = hx > 0 ? 0 : -100;
      const ay = vy > 0 ? 0 : -100;
      card.style.transform =
        `translate(${dot.x + hx * gap}px, ${dot.y + vy * gap}px) translate(${ax}%, ${ay}%)`;
      card.style.opacity = '1';
    }
  }, []);

  // Candidate card content, anchored near the district dot.
  useEffect(() => {
    const cont = overlay.current;
    if (!cont) return;
    if (!candidate) {
      if (cardRef.current) {
        cardRef.current.dataset.show = '0';
        cardRef.current.style.opacity = '0';
      }
      return;
    }
    let el = cardRef.current;
    if (!el) {
      el = document.createElement('div');
      el.className = 'otm-candidate';
      cont.appendChild(el);
      cardRef.current = el;
    }
    const pl = partyLabel(candidate.party);
    const party = pl ? `<span class="cand-party">${esc(pl)}</span>` : '';
    const raised = money(candidate.receipts);
    const indiv = money(candidate.individualTotal);
    const stats =
      raised || indiv
        ? `<div class="cand-stats">${raised ? `<span><b>${raised}</b> raised</span>` : ''}${
            indiv ? `<span><b>${indiv}</b> from individuals</span>` : ''
          }</div>`
        : '';
    const district = candidate.district
      ? `<div class="cand-district">${esc(candidate.district)}</div>`
      : '';
    el.innerHTML =
      `<div class="cand-head">` +
      `<span class="cand-avatar">${esc(initials(candidate.name))}</span>` +
      `<div class="cand-namecol"><div class="cand-name">${esc(formatName(candidate.name))}${party}</div>${district}</div>` +
      `</div>` +
      stats;
    el.dataset.show = '1';
    placeAll();
  }, [candidate, placeAll]);

  useEffect(() => {
    if (!container.current || mapRef.current) return;
    const el = container.current;
    const map = new maplibregl.Map({
      container: el,
      style: DARK_STYLE as maplibregl.StyleSpecification,
      center: [-93, 40],
      zoom: 3.4,
      attributionControl: { compact: true }, // collapsed "i" button by default
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
      offset: 18, // keep the tooltip off the cursor
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
    // Debounce the hide so moving the cursor across a label's edge (label <->
    // line) doesn't flicker: any new hover cancels the pending hide.
    let hideTimer: ReturnType<typeof setTimeout> | null = null;
    const showTip = (
      state: string | undefined,
      total: string | number | undefined,
      count: number | undefined,
      lngLat: maplibregl.LngLatLike,
    ) => {
      if (hideTimer) {
        clearTimeout(hideTimer);
        hideTimer = null;
      }
      map.getCanvas().style.cursor = 'pointer';
      setHover(state ?? null);
      const amt = Number(total ?? 0).toLocaleString('en-US', { maximumFractionDigits: 0 });
      const donors = count ? ` &middot; ${count} donor${count === 1 ? '' : 's'}` : '';
      popup.setLngLat(lngLat).setHTML(`<b>${state}</b> &middot; $${amt}${donors}`).addTo(map);
    };
    const hideTip = () => {
      if (hideTimer) clearTimeout(hideTimer);
      hideTimer = setTimeout(() => {
        hideTimer = null;
        map.getCanvas().style.cursor = '';
        setHover(null);
        popup.remove();
      }, 130);
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
      if (pulseRef.current) cancelAnimationFrame(pulseRef.current);
      if (animRef.current) cancelAnimationFrame(animRef.current);
      if (animTimeoutRef.current) clearTimeout(animTimeoutRef.current);
      map.remove();
      mapRef.current = null;
      ready.current = false;
    };
  }, [placeAll]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !scene) return;

    const placeMarker = (at: [number, number]) => {
      if (!markerRef.current) {
        const el = document.createElement('div');
        el.className = 'otm-pulse';
        markerRef.current = new maplibregl.Marker({ element: el }).setLngLat(at).addTo(map);
      } else {
        markerRef.current.setLngLat(at);
      }
    };
    // Pulse the district glow while funding is still loading.
    const startPulse = () => {
      if (pulseRef.current) return;
      const tick = (now: number) => {
        const phase = (Math.sin(now / 450) + 1) / 2;
        if (map.getLayer('otm-district-fill'))
          map.setPaintProperty('otm-district-fill', 'fill-opacity', 0.05 + phase * 0.18);
        if (map.getLayer('otm-district-line'))
          map.setPaintProperty('otm-district-line', 'line-opacity', 0.45 + phase * 0.55);
        pulseRef.current = requestAnimationFrame(tick);
      };
      pulseRef.current = requestAnimationFrame(tick);
    };
    const stopPulse = () => {
      if (pulseRef.current) {
        cancelAnimationFrame(pulseRef.current);
        pulseRef.current = null;
      }
      if (map.getLayer('otm-district-fill'))
        map.setPaintProperty('otm-district-fill', 'fill-opacity', 0.06);
      if (map.getLayer('otm-district-line'))
        map.setPaintProperty('otm-district-line', 'line-opacity', 0.9);
    };

    const clearFlows = () => {
      const f = map.getSource(FLOWS_SOURCE) as maplibregl.GeoJSONSource | undefined;
      const b = map.getSource(BUBBLES_SOURCE) as maplibregl.GeoJSONSource | undefined;
      f?.setData({ type: 'FeatureCollection', features: [] } as never);
      b?.setData({ type: 'FeatureCollection', features: [] } as never);
    };

    // Draw the money beams in one by one, closest state to furthest, each
    // growing outward from the district.
    const animateFlows = (sc: Scene, center: [number, number]) => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
      const home = sc.highlight.state.toUpperCase();
      const maxTotal = Math.max(1, ...sc.flows.map((f) => parseFloat(f.total) || 0));
      const items = sc.flows
        .map((f) => {
          const st = f.state.toUpperCase();
          const origin = STATE_CENTROIDS[st];
          if (!origin) return null;
          const amt = parseFloat(f.total) || 0;
          return { f, st, origin, amt, dist: Math.hypot(origin[0] - center[0], origin[1] - center[1]) };
        })
        .filter((x): x is NonNullable<typeof x> => x !== null)
        .sort((a, b) => a.dist - b.dist);
      const flowsSrc = map.getSource(FLOWS_SOURCE) as maplibregl.GeoJSONSource | undefined;
      const bubblesSrc = map.getSource(BUBBLES_SOURCE) as maplibregl.GeoJSONSource | undefined;
      const GROW = 700; // each beam draws over ~0.7s so the motion is legible
      const stagger = Math.min(140, 2600 / Math.max(items.length, 1));
      let start = 0;
      const frame = (now: number) => {
        if (!start) start = now;
        const elapsed = now - start;
        const lineFeats: unknown[] = [];
        const bubbleFeats: unknown[] = [];
        let done = true;
        items.forEach((it, i) => {
          const t = Math.max(0, Math.min(1, (elapsed - i * stagger) / GROW));
          if (t < 1) done = false;
          if (t <= 0) return;
          const e = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; // easeInOutCubic
          // Grow from the donor state toward the district - the way money flows.
          const tip: [number, number] = [
            it.origin[0] + (center[0] - it.origin[0]) * e,
            it.origin[1] + (center[1] - it.origin[1]) * e,
          ];
          lineFeats.push({
            type: 'Feature',
            geometry: { type: 'LineString', coordinates: [it.origin, tip] },
            properties: {
              state: it.st, total: it.f.total, count: it.f.count,
              outOfState: it.st !== home, width: 1.5 + (it.amt / maxTotal) * 7,
            },
          });
          // Donor bubble appears at the source as its beam starts.
          bubbleFeats.push({
            type: 'Feature',
            geometry: { type: 'Point', coordinates: it.origin },
            properties: {
              state: it.st, total: it.f.total, count: it.f.count,
              outOfState: it.st !== home, radius: 4 + Math.sqrt(it.amt / maxTotal) * 16,
            },
          });
        });
        flowsSrc?.setData({ type: 'FeatureCollection', features: lineFeats } as never);
        bubblesSrc?.setData({ type: 'FeatureCollection', features: bubbleFeats } as never);
        placeAll();
        if (!done) {
          animRef.current = requestAnimationFrame(frame);
        } else {
          animRef.current = null;
          animatingRef.current = false;
          applyScene(map as unknown as MapLike, sc); // canonical final data + hover state
          placeAll();
        }
      };
      animRef.current = requestAnimationFrame(frame);
    };

    const run = async () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
      if (animTimeoutRef.current) clearTimeout(animTimeoutRef.current);
      applyScene(map as unknown as MapLike, scene);

      const loading = !!scene.loading; // district known, funding still fetching
      const center: [number, number] = [scene.camera.lon, scene.camera.lat];
      if (!loading) {
        // Hide the just-applied beams right away so they don't flash before the
        // zoom-out and draw-in animation.
        animatingRef.current = true;
        clearFlows();
        placeMarker(center);
      }
      flowOriginsRef.current = loading
        ? []
        : scene.flows
            .map((f) => STATE_CENTROIDS[f.state.toUpperCase()])
            .filter((o): o is [number, number] => Array.isArray(o));

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
          // Labels capture pointer events (for hover), so forward the wheel to
          // the map or scroll-zoom breaks while hovering one.
          lab.addEventListener(
            'wheel',
            (ev) => {
              ev.preventDefault();
              map.getCanvasContainer().dispatchEvent(
                new WheelEvent('wheel', {
                  deltaX: ev.deltaX,
                  deltaY: ev.deltaY,
                  deltaMode: ev.deltaMode,
                  clientX: ev.clientX,
                  clientY: ev.clientY,
                  bubbles: true,
                  cancelable: true,
                }),
              );
            },
            { passive: false },
          );
          cont.appendChild(lab);
          labelsRef.current.push({ state: st, origin, amount: parseFloat(f.total) || 0, el: lab });
        }
      }
      hubRef.current = center;

      let districtGeom: { type: string; coordinates: unknown } | null = null;
      try {
        const key = `${scene.highlight.state}-${scene.highlight.district}`;
        const res = await fetch(`/districts/${key}.json`);
        if (res.ok) {
          const feature = await res.json();
          districtGeom = feature.geometry;
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

          // While loading we have no real camera yet; anchor the marker on the
          // district's own centroid.
          const centroid = feature.properties?.centroid as [number, number] | undefined;
          if (loading && Array.isArray(centroid)) {
            placeMarker(centroid);
            hubRef.current = centroid; // so the candidate card anchors on the dot
          }
        }
      } catch (e) {
        console.error('district boundary', e);
      }

      if (loading) {
        // Phase 1: district identified - pulse it, framed tight.
        loadingStartRef.current = performance.now();
        startPulse();
        clearFlows();
        if (districtGeom) {
          map.fitBounds(boundsOf(districtGeom), { padding: 70, duration: 1000, maxZoom: 12 });
        }
        placeAll();
        return;
      }

      // Phase 2: funding is in. Zoom out to fit every beam, then draw them one by
      // one (closest state first).
      const doPhase2 = () => {
        stopPulse();
        animatingRef.current = true;
        clearFlows();
        placeAll(); // hide labels while animating
        const bounds = new maplibregl.LngLatBounds();
        bounds.extend(center);
        if (districtGeom) {
          const [[x0, y0], [x1, y1]] = boundsOf(districtGeom) as [
            [number, number],
            [number, number],
          ];
          bounds.extend([x0, y0]);
          bounds.extend([x1, y1]);
        }
        for (const f of scene.flows) {
          const o = STATE_CENTROIDS[f.state.toUpperCase()];
          if (o) bounds.extend(o);
        }
        map.fitBounds(bounds, { padding: 110, duration: 1200, maxZoom: 9 });
        animTimeoutRef.current = setTimeout(() => animateFlows(scene, center), 1250);
      };
      // Even if funding is fast, keep the district framed (pulsing) at least 2s.
      const wait = Math.max(0, 2000 - (performance.now() - loadingStartRef.current));
      if (wait > 0) animTimeoutRef.current = setTimeout(doPhase2, wait);
      else doPhase2();
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
