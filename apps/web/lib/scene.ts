import type { Scene } from './types';
import { STATE_CENTROIDS } from './stateCentroids';

export interface MapLike {
  getSource(id: string): { setData(data: unknown): void } | undefined;
  addSource(id: string, src: Record<string, unknown>): void;
  addLayer(layer: Record<string, unknown>): void;
}

export const FLOWS_SOURCE = 'otm-flows';
export const FLOWS_HIT_LAYER = 'otm-flows-hit';
export const FLOW_LABELS_LAYER = 'otm-flow-labels';
export const BUBBLES_SOURCE = 'otm-bubbles';

type GeoJson = { type: 'FeatureCollection'; features: unknown[] };

function maxTotal(scene: Scene): number {
  return Math.max(1, ...scene.flows.map((f) => parseFloat(f.total) || 0));
}

export function sceneToFlows(scene: Scene): GeoJson {
  const center: [number, number] = [scene.camera.lon, scene.camera.lat];
  const home = scene.highlight.state.toUpperCase();
  const max = maxTotal(scene);
  const features: unknown[] = [];
  for (const f of scene.flows) {
    const st = f.state.toUpperCase();
    const origin = STATE_CENTROIDS[st];
    if (!origin) continue;
    const amt = parseFloat(f.total) || 0;
    features.push({
      type: 'Feature',
      geometry: { type: 'LineString', coordinates: [origin, center] },
      properties: {
        state: st, total: f.total, count: f.count,
        outOfState: st !== home, width: 1.5 + (amt / max) * 7,
      },
    });
  }
  return { type: 'FeatureCollection', features };
}

export function sceneToBubbles(scene: Scene): GeoJson {
  const home = scene.highlight.state.toUpperCase();
  const max = maxTotal(scene);
  const features: unknown[] = [];
  for (const f of scene.flows) {
    const st = f.state.toUpperCase();
    const origin = STATE_CENTROIDS[st];
    if (!origin) continue;
    const amt = parseFloat(f.total) || 0;
    features.push({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: origin },
      properties: {
        state: st, total: f.total, count: f.count,
        // area (not radius) proportional to dollars -> radius scales with sqrt
        outOfState: st !== home, radius: 4 + Math.sqrt(amt / max) * 16,
      },
    });
  }
  return { type: 'FeatureCollection', features };
}

const COLOR = ['case', ['get', 'outOfState'], '#ff9d3c', '#3ddc84'];
const HOVER = ['boolean', ['feature-state', 'hover'], false];

// Add a source (promoting `state` to the feature id so hover feature-state can
// key on it) plus its layers, once. Returns false if it already existed.
function upsertSource(map: MapLike, id: string, data: GeoJson): boolean {
  const src = map.getSource(id);
  if (src) {
    src.setData(data);
    return false;
  }
  map.addSource(id, { type: 'geojson', data, promoteId: 'state' });
  return true;
}

export function applyScene(map: MapLike, scene: Scene): void {
  const flowsNew = upsertSource(map, FLOWS_SOURCE, sceneToFlows(scene));
  if (flowsNew) {
    map.addLayer({
      id: FLOWS_SOURCE,
      type: 'line',
      source: FLOWS_SOURCE,
      layout: { 'line-cap': 'round' },
      paint: {
        'line-color': COLOR,
        'line-width': ['case', HOVER, ['*', ['get', 'width'], 1.9], ['get', 'width']],
        'line-blur': ['*', ['get', 'width'], 0.6],
        'line-opacity': ['case', HOVER, 1, 0.75],
      },
    });
    // wide, invisible line for an easy hover target
    map.addLayer({
      id: FLOWS_HIT_LAYER,
      type: 'line',
      source: FLOWS_SOURCE,
      paint: { 'line-color': '#000000', 'line-width': 16, 'line-opacity': 0 },
    });
  }
  if (upsertSource(map, BUBBLES_SOURCE, sceneToBubbles(scene))) {
    map.addLayer({
      id: BUBBLES_SOURCE,
      type: 'circle',
      source: BUBBLES_SOURCE,
      paint: {
        'circle-radius': ['case', HOVER, ['*', ['get', 'radius'], 1.3], ['get', 'radius']],
        'circle-color': COLOR,
        'circle-opacity': ['case', HOVER, 0.6, 0.32],
        'circle-blur': 0.4,
        'circle-stroke-color': COLOR,
        'circle-stroke-width': ['case', HOVER, 2.5, 1],
        'circle-stroke-opacity': 0.85,
      },
    });
  }
  if (flowsNew) {
    // state codes ride each beam; MapLibre collision keeps them from
    // overlapping and repositions them as you zoom. Added last, so on top.
    map.addLayer({
      id: FLOW_LABELS_LAYER,
      type: 'symbol',
      source: FLOWS_SOURCE,
      layout: {
        'symbol-placement': 'line',
        // spacing larger than any on-screen beam => exactly one label per beam
        // (no duplicates), while keeping labels along the beams near the hub.
        'symbol-spacing': 3000,
        'text-field': ['get', 'state'],
        'text-font': ['Open Sans Semibold'],
        'text-size': 11,
        'text-allow-overlap': false,
        'text-padding': 8,
        'text-keep-upright': true,
      },
      paint: {
        'text-color': '#e6edf3',
        'text-halo-color': '#0d1117',
        'text-halo-width': 1.6,
      },
    });
  }
}
