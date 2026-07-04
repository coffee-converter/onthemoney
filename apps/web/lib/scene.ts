import type { Scene } from './types';

export interface MapLike {
  flyTo(opts: Record<string, unknown>): void;
  getSource(id: string): { setData(data: unknown): void } | undefined;
  addSource(id: string, src: Record<string, unknown>): void;
  addLayer(layer: Record<string, unknown>): void;
  getLayer(id: string): unknown;
}

export const HIGHLIGHT_SOURCE = 'otm-highlight';
export const FLOWS_SOURCE = 'otm-flows';

type GeoJson = { type: 'FeatureCollection'; features: unknown[] };

export function sceneToHighlight(scene: Scene): GeoJson {
  return {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [scene.camera.lon, scene.camera.lat],
        },
        properties: {
          label: `${scene.highlight.state}-${scene.highlight.district}`,
        },
      },
    ],
  };
}

export function sceneToFlows(scene: Scene): GeoJson {
  const center: [number, number] = [scene.camera.lon, scene.camera.lat];
  const n = Math.max(scene.flows.length, 1);
  const features = scene.flows.map((f, i) => {
    const angle = (i / n) * Math.PI * 2;
    const start: [number, number] = [
      center[0] + Math.cos(angle) * 1.5,
      center[1] + Math.sin(angle) * 1.5,
    ];
    return {
      type: 'Feature',
      geometry: { type: 'LineString', coordinates: [start, center] },
      properties: { label: f.label, amount: f.amount },
    };
  });
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

// applyScene is how the agent "steers the world": it flies the camera to the
// district and paints the money flows and the highlight from the scene spec
// the agent emitted.
export function applyScene(map: MapLike, scene: Scene): void {
  map.flyTo({
    center: [scene.camera.lon, scene.camera.lat],
    zoom: scene.camera.zoom,
    essential: true,
  });
  upsert(map, FLOWS_SOURCE, sceneToFlows(scene), {
    id: FLOWS_SOURCE,
    type: 'line',
    source: FLOWS_SOURCE,
    paint: { 'line-color': '#4aa3ff', 'line-width': 2, 'line-opacity': 0.7 },
  });
  upsert(map, HIGHLIGHT_SOURCE, sceneToHighlight(scene), {
    id: HIGHLIGHT_SOURCE,
    type: 'circle',
    source: HIGHLIGHT_SOURCE,
    paint: { 'circle-radius': 8, 'circle-color': '#ffd24a', 'circle-opacity': 0.85 },
  });
}
