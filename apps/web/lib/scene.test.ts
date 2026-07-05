import { describe, it, expect, vi } from 'vitest';
import {
  applyScene,
  sceneToFlows,
  sceneToBubbles,
  FLOWS_SOURCE,
  BUBBLES_SOURCE,
  type MapLike,
} from './scene';
import type { Scene } from './types';

const SCENE: Scene = {
  camera: { type: 'flyTo', lon: -88, lat: 42, zoom: 7 },
  highlight: { state: 'IL', district: '05' },
  flows: [
    { state: 'IL', total: '5000.00', count: 12 },
    { state: 'CA', total: '1000.00', count: 3 },
  ],
};

function fakeMap() {
  const sources = new Map<string, { setData: ReturnType<typeof vi.fn> }>();
  const layers = new Set<string>();
  return {
    getSource: vi.fn((id: string) => sources.get(id)),
    addSource: vi.fn((id: string) => sources.set(id, { setData: vi.fn() })),
    addLayer: vi.fn((layer: { id: string }) => layers.add(layer.id)),
    getLayer: vi.fn((id: string) => (layers.has(id) ? id : undefined)),
    _sources: sources,
  };
}

describe('scene flows', () => {
  it('builds one line per contributor state with a known centroid', () => {
    expect(sceneToFlows(SCENE).features).toHaveLength(2);
  });

  it('scales width by dollars and tags in vs out-of-state', () => {
    const feats = sceneToFlows(SCENE).features as Array<{
      properties: { state: string; outOfState: boolean; width: number };
    }>;
    const il = feats.find((f) => f.properties.state === 'IL')!;
    const ca = feats.find((f) => f.properties.state === 'CA')!;
    expect(il.properties.outOfState).toBe(false);
    expect(ca.properties.outOfState).toBe(true);
    expect(il.properties.width).toBeGreaterThan(ca.properties.width);
  });

  it('builds a bubble per state sized by dollars', () => {
    const feats = sceneToBubbles(SCENE).features as Array<{
      properties: { state: string; radius: number };
    }>;
    expect(feats).toHaveLength(2);
    const il = feats.find((f) => f.properties.state === 'IL')!;
    const ca = feats.find((f) => f.properties.state === 'CA')!;
    expect(il.properties.radius).toBeGreaterThan(ca.properties.radius);
  });

  it('adds the flow and bubble layers once, then updates on re-apply', () => {
    const map = fakeMap();
    applyScene(map as unknown as MapLike, SCENE);
    expect(map.addSource).toHaveBeenCalledTimes(2);
    expect(map.addLayer).toHaveBeenCalledTimes(2);
    applyScene(map as unknown as MapLike, SCENE);
    expect(map.addSource).toHaveBeenCalledTimes(2);
    expect(map._sources.get(FLOWS_SOURCE)!.setData).toHaveBeenCalled();
    expect(map._sources.get(BUBBLES_SOURCE)!.setData).toHaveBeenCalled();
  });
});
