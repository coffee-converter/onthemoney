import { describe, it, expect, vi } from 'vitest';
import {
  applyScene,
  sceneToFlows,
  sceneToHighlight,
  FLOWS_SOURCE,
  HIGHLIGHT_SOURCE,
  type MapLike,
} from './scene';
import type { Scene } from './types';

const SCENE: Scene = {
  camera: { type: 'flyTo', lon: -110.5, lat: 32.0, zoom: 7 },
  highlight: { state: 'AZ', district: '06' },
  flows: [
    { label: 'DOE, JOHN', employer: 'ACME', amount: '500.00', state: 'AZ' },
    { label: 'ROE, JANE', employer: 'SELF', amount: '250.00', state: 'NY' },
  ],
};

function fakeMap() {
  const sources = new Map<string, { setData: ReturnType<typeof vi.fn> }>();
  const layers = new Set<string>();
  return {
    flyTo: vi.fn(),
    getSource: vi.fn((id: string) => sources.get(id)),
    addSource: vi.fn((id: string) => {
      sources.set(id, { setData: vi.fn() });
    }),
    addLayer: vi.fn((layer: { id: string }) => {
      layers.add(layer.id);
    }),
    getLayer: vi.fn((id: string) => (layers.has(id) ? id : undefined)),
    _sources: sources,
  };
}

describe('scene mapping', () => {
  it('builds one highlight feature at the camera centroid', () => {
    const gj = sceneToHighlight(SCENE);
    expect(gj.features).toHaveLength(1);
  });

  it('builds one flow line per donor with a known state', () => {
    expect(sceneToFlows(SCENE).features).toHaveLength(2);
  });

  it('tags in-state vs out-of-state donors', () => {
    const feats = sceneToFlows(SCENE).features as Array<{
      properties: { label: string; outOfState: boolean };
    }>;
    const az = feats.find((f) => f.properties.label === 'DOE, JOHN');
    const ny = feats.find((f) => f.properties.label === 'ROE, JANE');
    expect(az?.properties.outOfState).toBe(false); // home state AZ
    expect(ny?.properties.outOfState).toBe(true);
  });

  it('skips donors whose state has no centroid', () => {
    const noState = { ...SCENE, flows: [{ label: 'X', employer: 'Y', amount: '1.00' }] };
    expect(sceneToFlows(noState).features).toHaveLength(0);
  });

  it('flies the camera and adds both layers on first apply', () => {
    const map = fakeMap();
    applyScene(map as unknown as MapLike, SCENE);
    expect(map.flyTo).toHaveBeenCalledWith(
      expect.objectContaining({ center: [-110.5, 32.0], zoom: 7 }),
    );
    expect(map.addSource).toHaveBeenCalledTimes(2);
    expect(map.addLayer).toHaveBeenCalledTimes(2);
  });

  it('updates existing sources on second apply instead of re-adding', () => {
    const map = fakeMap();
    applyScene(map as unknown as MapLike, SCENE);
    applyScene(map as unknown as MapLike, SCENE);
    // still only two sources created total
    expect(map.addSource).toHaveBeenCalledTimes(2);
    expect(map._sources.get(FLOWS_SOURCE)!.setData).toHaveBeenCalled();
    expect(map._sources.get(HIGHLIGHT_SOURCE)!.setData).toHaveBeenCalled();
  });
});
