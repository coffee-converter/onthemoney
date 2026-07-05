import type { Scene } from './types';
import { STATE_CENTROIDS } from './stateCentroids';

export interface MapLike {
  getSource(id: string): { setData(data: unknown): void } | undefined;
  addSource(id: string, src: Record<string, unknown>): void;
  addLayer(layer: Record<string, unknown>): void;
  getLayer(id: string): unknown;
}

export const FLOWS_SOURCE = 'otm-flows';

type GeoJson = { type: 'FeatureCollection'; features: unknown[] };

function flowWidth(amount: string, max: number): number {
  const a = parseFloat(amount) || 0;
  return 1.5 + (max > 0 ? (a / max) * 6 : 0); // 1.5 .. 7.5 px by dollar amount
}

// One line per donor, from their home state's centroid into the district.
// Width scales with the donation; in-state and out-of-state are tagged so they
// can be colored apart.
export function sceneToFlows(scene: Scene): GeoJson {
  const center: [number, number] = [scene.camera.lon, scene.camera.lat];
  const home = scene.highlight.state.toUpperCase();
  const max = Math.max(1, ...scene.flows.map((f) => parseFloat(f.amount) || 0));
  const features: unknown[] = [];
  for (const f of scene.flows) {
    const st = (f.state || '').toUpperCase();
    const origin = STATE_CENTROIDS[st];
    if (!origin) continue;
    features.push({
      type: 'Feature',
      geometry: { type: 'LineString', coordinates: [origin, center] },
      properties: {
        label: f.label,
        amount: f.amount,
        outOfState: st !== home,
        width: flowWidth(f.amount, max),
      },
    });
  }
  return { type: 'FeatureCollection', features };
}

// applyScene paints the donor money flows. Basemap, the district boundary, and
// the convergence marker are handled by the map component.
export function applyScene(map: MapLike, scene: Scene): void {
  const data = sceneToFlows(scene);
  const src = map.getSource(FLOWS_SOURCE);
  if (src) {
    src.setData(data);
    return;
  }
  map.addSource(FLOWS_SOURCE, { type: 'geojson', data });
  map.addLayer({
    id: FLOWS_SOURCE,
    type: 'line',
    source: FLOWS_SOURCE,
    layout: { 'line-cap': 'round' },
    paint: {
      'line-color': ['case', ['get', 'outOfState'], '#ff9d3c', '#3ddc84'],
      'line-width': ['get', 'width'],
      'line-blur': ['*', ['get', 'width'], 0.6],
      'line-opacity': 0.85,
    },
  });
}
