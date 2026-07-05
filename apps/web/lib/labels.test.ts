import { describe, it, expect } from 'vitest';
import {
  clipSegment,
  placeLabels,
  labelSpot,
  largestRing,
  type LabelInput,
  type Pt,
} from './labels';

const RECT = { xmin: 0, ymin: 0, xmax: 100, ymax: 100 };

describe('clipSegment', () => {
  it('keeps a segment fully inside', () => {
    const c = clipSegment({ x: 10, y: 10 }, { x: 90, y: 90 }, RECT)!;
    expect(c.ax).toBeCloseTo(10);
    expect(c.bx).toBeCloseTo(90);
  });

  it('clips a segment that exits the rect', () => {
    const c = clipSegment({ x: 50, y: 50 }, { x: 200, y: 50 }, RECT)!;
    expect(c.bx).toBeCloseTo(100); // clamped to the right edge
  });

  it('returns null when the segment misses the rect', () => {
    expect(clipSegment({ x: 200, y: 200 }, { x: 300, y: 300 }, RECT)).toBeNull();
  });
});

// project treats the lng/lat as raw screen coords for deterministic tests.
const project = (p: [number, number]): Pt => ({ x: p[0], y: p[1] });

describe('placeLabels', () => {
  it('places a visible label on an on-screen beam', () => {
    const labels: LabelInput[] = [{ state: 'CA', origin: [20, 20], amount: 100 }];
    const [p] = placeLabels(labels, { x: 90, y: 90 }, project, 100, 100, 0);
    expect(p.visible).toBe(true);
    expect(p.x).toBeGreaterThan(0);
  });

  it('hides the lower-dollar label when two crowd a short beam', () => {
    // A short beam leaves no room to slide the second label clear.
    const labels: LabelInput[] = [
      { state: 'CA', origin: [20, 20], amount: 100 },
      { state: 'NY', origin: [20, 20], amount: 10 },
    ];
    const res = placeLabels(labels, { x: 24, y: 24 }, project, 100, 100, 0);
    const ca = res.find((r) => r.state === 'CA')!;
    const ny = res.find((r) => r.state === 'NY')!;
    expect(ca.visible).toBe(true); // bigger dollars win
    expect(ny.visible).toBe(false);
  });

  it('hides a label whose beam is entirely off screen', () => {
    const labels: LabelInput[] = [{ state: 'TX', origin: [300, 300], amount: 100 }];
    const [p] = placeLabels(labels, { x: 200, y: 200 }, project, 100, 100, 0);
    expect(p.visible).toBe(false);
  });
});

describe('district watermark placement', () => {
  const SQUARE: [number, number][] = [
    [0, 0],
    [0, 10],
    [10, 10],
    [10, 0],
    [0, 0],
  ];

  it('finds the center of a square and its inscribed radius', () => {
    const s = labelSpot(SQUARE, 20);
    expect(s.x).toBeCloseTo(5, 1);
    expect(s.y).toBeCloseTo(5, 1);
    expect(s.r).toBeCloseTo(5, 1);
  });

  it('picks the larger polygon of a MultiPolygon', () => {
    const geom = {
      type: 'MultiPolygon',
      coordinates: [
        [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]], // small
        [[[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]], // big
      ],
    };
    expect(largestRing(geom)).toHaveLength(5);
    expect(labelSpot(largestRing(geom), 20).r).toBeCloseTo(5, 1);
  });
});
