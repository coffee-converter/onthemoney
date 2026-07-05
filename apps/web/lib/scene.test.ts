import { describe, it, expect, vi } from 'vitest';
import { applyScene, sceneToFlows, FLOWS_SOURCE, type MapLike } from './scene';
import type { Scene } from './types';

const SCENE: Scene = {
  camera: { type: 'flyTo', lon: -88, lat: 42, zoom: 7 },
  highlight: { state: 'IL', district: '05' },
  flows: [
    { label: 'BIG', employer: 'x', amount: '5000.00', state: 'IL' },
    { label: 'SMALL', employer: 'y', amount: '1000.00', state: 'CA' },
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
  it('builds one line per donor with a known state', () => {
    expect(sceneToFlows(SCENE).features).toHaveLength(2);
  });

  it('scales width by amount and tags in vs out-of-state', () => {
    const feats = sceneToFlows(SCENE).features as Array<{
      properties: { label: string; outOfState: boolean; width: number };
    }>;
    const big = feats.find((f) => f.properties.label === 'BIG')!;
    const small = feats.find((f) => f.properties.label === 'SMALL')!;
    expect(big.properties.outOfState).toBe(false); // IL is the home state
    expect(small.properties.outOfState).toBe(true); // CA
    expect(big.properties.width).toBeGreaterThan(small.properties.width);
  });

  it('skips donors whose state has no centroid', () => {
    const s = { ...SCENE, flows: [{ label: 'X', employer: 'y', amount: '1.00' }] };
    expect(sceneToFlows(s).features).toHaveLength(0);
  });

  it('adds the flows source and layer once, then updates on re-apply', () => {
    const map = fakeMap();
    applyScene(map as unknown as MapLike, SCENE);
    expect(map.addSource).toHaveBeenCalledTimes(1);
    expect(map.addLayer).toHaveBeenCalledTimes(1);
    applyScene(map as unknown as MapLike, SCENE);
    expect(map.addSource).toHaveBeenCalledTimes(1);
    expect(map._sources.get(FLOWS_SOURCE)!.setData).toHaveBeenCalled();
  });
});
