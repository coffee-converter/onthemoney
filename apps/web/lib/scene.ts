import type { Scene } from './types';
import { STATE_CENTROIDS } from './stateCentroids';

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

// One line per donor, from their home state's centroid into the district.
// In-state and out-of-state flows are tagged so they can be colored apart.
export function sceneToFlows(scene: Scene): GeoJson {
  const center: [number, number] = [scene.camera.lon, scene.camera.lat];
  const homeState = scene.highlight.state.toUpperCase();
  const features: unknown[] = [];
  for (const f of scene.flows) {
    const st = (f.state || '').toUpperCase();
    const origin = STATE_CENTROIDS[st];
    if (!origin) continue;
    features.push({
      type: 'Feature',
      geometry: { type: 'LineString', coordinates: [origin, center] },
      properties: { label: f.label, amount: f.amount, outOfState: st !== homeState },
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

// applyScene is how the agent "steers the world": it flies the camera to the
// district and paints the donor money flows and the highlight from the scene
// spec the agent emitted.
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
    paint: {
      // in-state money green, out-of-state money orange
      'line-color': ['case', ['get', 'outOfState'], '#e08a4a', '#37c871'],
      'line-width': 1.6,
      'line-opacity': 0.75,
    },
  });
  upsert(map, HIGHLIGHT_SOURCE, sceneToHighlight(scene), {
    id: HIGHLIGHT_SOURCE,
    type: 'circle',
    source: HIGHLIGHT_SOURCE,
    paint: { 'circle-radius': 8, 'circle-color': '#ffd24a', 'circle-opacity': 0.9 },
  });
}
