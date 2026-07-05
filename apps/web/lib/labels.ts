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

// Centered horizontal/vertical half-extents of the polygon through a point -
// how far the shape reaches left/right and up/down before an edge. Lets an
// elongated district fit much larger horizontal text than an inscribed circle.
export function chordExtents(
  ring: LngLat[],
  px: number,
  py: number,
): { halfW: number; halfH: number } {
  let left = Infinity;
  let right = Infinity;
  let up = Infinity;
  let down = Infinity;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [x1, y1] = ring[i];
    const [x2, y2] = ring[j];
    if (y1 > py !== y2 > py) {
      const xc = x1 + ((py - y1) / (y2 - y1)) * (x2 - x1);
      const dx = xc - px;
      if (dx >= 0) right = Math.min(right, dx);
      else left = Math.min(left, -dx);
    }
    if (x1 > px !== x2 > px) {
      const yc = y1 + ((px - x1) / (x2 - x1)) * (y2 - y1);
      const dy = yc - py;
      if (dy >= 0) up = Math.min(up, dy);
      else down = Math.min(down, -dy);
    }
  }
  const halfW = Math.min(left, right);
  const halfH = Math.min(up, down);
  return {
    halfW: Number.isFinite(halfW) ? halfW : 0,
    halfH: Number.isFinite(halfH) ? halfH : 0,
  };
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

const NEAR = 46; // keep labels off the hub
const MARGIN = 26; // keep labels off the viewport edge
// Along-beam offsets (px) tried when the target spot is taken - nudging a label
// in/out along its own line keeps it visually tied to its beam.
const ALONG = [0, 24, -24, 48, -48, 72, -72, 100, -100, 130, -130];

// Labels are spaced by distance RANK (not raw distance), so far outliers like
// HI and AK don't compress every continental label toward the hub. Rank is
// monotonic in distance, so a closer state still sits nearer the district.
export function placeLabels(
  labels: LabelInput[],
  hub: Pt,
  hubLngLat: [number, number],
  project: (lnglat: [number, number]) => Pt,
  width: number,
  height: number,
  pad = 22,
): Placement[] {
  const rect: Rect = { xmin: pad, ymin: pad, xmax: width - pad, ymax: height - pad };
  const withDist = labels.map((L) => ({
    L,
    s: project(L.origin),
    dist: Math.hypot(L.origin[0] - hubLngLat[0], L.origin[1] - hubLngLat[1]),
  }));
  // Even fraction 0..1 by distance rank -> labels spread across the whole span.
  const ranked = [...withDist].sort((a, b) => a.dist - b.dist);
  const fracOf = new Map<string, number>();
  ranked.forEach((e, i) =>
    fracOf.set(e.L.state, ranked.length <= 1 ? 0.6 : i / (ranked.length - 1)),
  );
  const placed: Box[] = [];
  // Biggest dollars first so the important labels claim their spot.
  const order = [...withDist].sort((a, b) => b.L.amount - a.L.amount);
  const out: Placement[] = [];
  for (const e of order) {
    const seg = clipSegment(hub, e.s, rect);
    let placement: Placement = { state: e.L.state, x: 0, y: 0, visible: false };
    if (seg) {
      const dA = Math.hypot(seg.ax - hub.x, seg.ay - hub.y);
      const dB = Math.hypot(seg.bx - hub.x, seg.by - hub.y);
      const lo = Math.min(dA + NEAR, dB);
      const hi = Math.max(dB - MARGIN, lo);
      const target = lo + (fracOf.get(e.L.state) ?? 0.6) * (hi - lo);
      const beamLen = Math.hypot(e.s.x - hub.x, e.s.y - hub.y) || 1;
      const ux = (e.s.x - hub.x) / beamLen;
      const uy = (e.s.y - hub.y) / beamLen;
      const w = e.L.state.length * 8 + 12;
      const h = 18;
      // Dodge overlaps by nudging along the beam (in/out), staying on the line.
      for (const delta of ALONG) {
        const d = Math.min(Math.max(target + delta, dA), dB);
        const x = hub.x + ux * d;
        const y = hub.y + uy * d;
        if (x < rect.xmin || x > rect.xmax || y < rect.ymin || y > rect.ymax) continue;
        const box: Box = { x0: x - w / 2, y0: y - h / 2, x1: x + w / 2, y1: y + h / 2 };
        if (!placed.some((p) => overlaps(p, box))) {
          placed.push(box);
          placement = { state: e.L.state, x, y, visible: true };
          break;
        }
      }
    }
    out.push(placement);
  }
  return out;
}
