import type { Scene } from './types';
import { STATE_CENTROIDS } from './stateCentroids';

export interface MapLike {
  getSource(id: string): { setData(data: unknown): void } | undefined;
  addSource(id: string, src: Record<string, unknown>): void;
  addLayer(layer: Record<string, unknown>): void;
  getLayer(id: string): unknown;
}

export const FLOWS_SOURCE = 'otm-flows';
export const BUBBLES_SOURCE = 'otm-bubbles';

type GeoJson = { type: 'FeatureCollection'; features: unknown[] };

function maxTotal(scene: Scene): number {
  return Math.max(1, ...scene.flows.map((f) => parseFloat(f.total) || 0));
}

// One weighted line per contributor state, from that state's centroid into the
// district. Width scales with the dollars from that state; in-state and
// out-of-state are tagged so they can be colored apart.
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
        state: st,
        total: f.total,
        count: f.count,
        outOfState: st !== home,
        width: 1.5 + (amt / max) * 7,
      },
    });
  }
  return { type: 'FeatureCollection', features };
}

// A bubble at each contributor state, sized by the dollars from that state.
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
        state: st,
        total: f.total,
        count: f.count,
        outOfState: st !== home,
        radius: 4 + (amt / max) * 18,
      },
    });
  }
  return { type: 'FeatureCollection', features };
}

function upsert(
  map: MapLike,
  id: string,
  data: GeoJson,
  layer: Record<string, unknown>,
): void {
  const src = map.getSource(id);
  if (src) {
    src.setData(data);
    return;
  }
  map.addSource(id, { type: 'geojson', data });
  if (!map.getLayer(id)) map.addLayer(layer);
}

const COLOR = ['case', ['get', 'outOfState'], '#ff9d3c', '#3ddc84'];

export function applyScene(map: MapLike, scene: Scene): void {
  upsert(map, FLOWS_SOURCE, sceneToFlows(scene), {
    id: FLOWS_SOURCE,
    type: 'line',
    source: FLOWS_SOURCE,
    layout: { 'line-cap': 'round' },
    paint: {
      'line-color': COLOR,
      'line-width': ['get', 'width'],
      'line-blur': ['*', ['get', 'width'], 0.6],
      'line-opacity': 0.8,
    },
  });
  upsert(map, BUBBLES_SOURCE, sceneToBubbles(scene), {
    id: BUBBLES_SOURCE,
    type: 'circle',
    source: BUBBLES_SOURCE,
    paint: {
      'circle-radius': ['get', 'radius'],
      'circle-color': COLOR,
      'circle-opacity': 0.35,
      'circle-blur': 0.4,
      'circle-stroke-color': COLOR,
      'circle-stroke-width': 1,
      'circle-stroke-opacity': 0.8,
    },
  });
}
