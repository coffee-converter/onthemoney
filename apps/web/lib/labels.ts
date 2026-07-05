// Dynamic map-label placement. Each state label rides its beam and is kept on
// screen: we project the beam to pixels, clip it to the viewport, and drop the
// label at a point on the visible segment - biggest-dollar labels win space so
// crowded areas thin out instead of overlapping.

export interface Pt {
  x: number;
  y: number;
}

export interface LabelInput {
  state: string;
  origin: [number, number]; // state centroid, lng/lat
  amount: number;
}

export interface Placement {
  state: string;
  x: number;
  y: number;
  visible: boolean;
}

interface Rect {
  xmin: number;
  ymin: number;
  xmax: number;
  ymax: number;
}

interface Box {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

// Liang-Barsky: clip segment p0->p1 to rect. Returns the visible sub-segment
// (a = p0 side, b = p1 side) or null if the segment misses the rect entirely.
export function clipSegment(
  p0: Pt,
  p1: Pt,
  r: Rect,
): { ax: number; ay: number; bx: number; by: number } | null {
  let t0 = 0;
  let t1 = 1;
  const dx = p1.x - p0.x;
  const dy = p1.y - p0.y;
  const tests: [number, number][] = [
    [-dx, p0.x - r.xmin],
    [dx, r.xmax - p0.x],
    [-dy, p0.y - r.ymin],
    [dy, r.ymax - p0.y],
  ];
  for (const [p, q] of tests) {
    if (p === 0) {
      if (q < 0) return null; // parallel to this edge and outside it
    } else {
      const t = q / p;
      if (p < 0) {
        if (t > t1) return null;
        if (t > t0) t0 = t;
      } else {
        if (t < t0) return null;
        if (t < t1) t1 = t;
      }
    }
  }
  return {
    ax: p0.x + t0 * dx,
    ay: p0.y + t0 * dy,
    bx: p0.x + t1 * dx,
    by: p0.y + t1 * dy,
  };
}

function overlaps(a: Box, b: Box, m = 3): boolean {
  return !(b.x0 > a.x1 + m || b.x1 < a.x0 - m || b.y0 > a.y1 + m || b.y1 < a.y0 - m);
}

// --- District watermark placement ---------------------------------------
// Find the point inside the polygon farthest from any edge (pole of
// inaccessibility) so the district code sits in the largest open area, plus
// that distance (r) so the caller can size the text to fit.

type LngLat = [number, number];

function ringSignedArea(ring: LngLat[]): number {
  let a = 0;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    a += ring[j][0] * ring[i][1] - ring[i][0] * ring[j][1];
  }
  return a / 2;
}

export function largestRing(geom: { type: string; coordinates: unknown }): LngLat[] {
  const outers: LngLat[][] =
    geom.type === 'MultiPolygon'
      ? (geom.coordinates as LngLat[][][]).map((poly) => poly[0])
      : [(geom.coordinates as LngLat[][])[0]];
  let best = outers[0];
  let bestArea = -Infinity;
  for (const ring of outers) {
    const area = Math.abs(ringSignedArea(ring));
    if (area > bestArea) {
      bestArea = area;
      best = ring;
    }
  }
  return best;
}

function pointInRing(x: number, y: number, ring: LngLat[]): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

function distToSeg(px: number, py: number, a: LngLat, b: LngLat): number {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const l2 = dx * dx + dy * dy;
  let t = l2 ? ((px - a[0]) * dx + (py - a[1]) * dy) / l2 : 0;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(px - (a[0] + t * dx), py - (a[1] + t * dy));
}

function distToRing(x: number, y: number, ring: LngLat[]): number {
  let min = Infinity;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    min = Math.min(min, distToSeg(x, y, ring[i], ring[j]));
  }
  return min;
}

export function labelSpot(ring: LngLat[], n = 40): { x: number; y: number; r: number } {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const [x, y] of ring) {
    if (x < minX) minX = x;
    if (y < minY) minY = y;
    if (x > maxX) maxX = x;
    if (y > maxY) maxY = y;
  }
  let best = { x: (minX + maxX) / 2, y: (minY + maxY) / 2, r: 0 };
  for (let i = 0; i <= n; i++) {
    for (let j = 0; j <= n; j++) {
      const x = minX + ((maxX - minX) * i) / n;
      const y = minY + ((maxY - minY) * j) / n;
      if (!pointInRing(x, y, ring)) continue;
      const r = distToRing(x, y, ring);
      if (r > best.r) best = { x, y, r };
    }
  }
  return best;
}

// Fractions along the visible segment (from state end toward hub) to try when
// the preferred spot is taken - lets a label slide inward to dodge neighbors.
const SLOTS = [0.8, 0.62, 0.44, 0.28];

export function placeLabels(
  labels: LabelInput[],
  hub: Pt,
  project: (lnglat: [number, number]) => Pt,
  width: number,
  height: number,
  pad = 22,
): Placement[] {
  const rect: Rect = { xmin: pad, ymin: pad, xmax: width - pad, ymax: height - pad };
  const placed: Box[] = [];
  // Biggest dollars first so the most important labels claim space.
  const order = [...labels].sort((a, b) => b.amount - a.amount);
  const out: Placement[] = [];
  for (const L of order) {
    const s = project(L.origin);
    const seg = clipSegment(hub, s, rect);
    let placement: Placement = { state: L.state, x: 0, y: 0, visible: false };
    if (seg) {
      const w = L.state.length * 8 + 12;
      const h = 18;
      for (const f of SLOTS) {
        const x = seg.ax + f * (seg.bx - seg.ax);
        const y = seg.ay + f * (seg.by - seg.ay);
        const box: Box = { x0: x - w / 2, y0: y - h / 2, x1: x + w / 2, y1: y + h / 2 };
        if (!placed.some((p) => overlaps(p, box))) {
          placed.push(box);
          placement = { state: L.state, x, y, visible: true };
          break;
        }
      }
    }
    out.push(placement);
  }
  return out;
}
