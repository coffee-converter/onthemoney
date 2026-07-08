import { ImageResponse } from 'next/og';

// Generated social-share image (1200x630). Next wires this into og:image/twitter:image.
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';
export const alt = 'On The Money — U.S. House campaign finance atlas';

const ACCENT = '#4aa3ff';
const IN = '#3ddc84'; // in-state money — matches the app's map legend
const OUT = '#ff9d3c'; // out-of-state money
const CHIPS = ['Grounded', 'Cited', 'Calibrated'];

// Faint "money-flow beams" like the app's map: donor states (dots) sending
// money along thin lines to one district (the hub). Green = the in-state home,
// amber = out-of-state donors — the app's own legend, deliberately not
// partisan red/blue. Hub is offset from center so it doesn't sit behind the text.
// Two faint money-flow diagrams flanking the text: each is a blue district hub
// with a cluster of donor dots (one green in-state home, the rest amber
// out-of-state) beaming in at varied lengths for an organic look.
const HUBS = [
  { x: 195, y: 315 },
  { x: 1005, y: 315 },
];
// [angleDeg, radius] spokes — radii vary so the beams aren't uniform.
const SPOKES = [
  [[-152, 150], [-108, 206], [-62, 120], [-18, 184], [28, 150], [70, 214], [118, 134], [158, 196], [196, 166]],
  [[-166, 176], [-122, 128], [-74, 206], [-28, 150], [18, 198], [64, 120], [112, 200], [152, 142], [188, 182]],
];
const GREEN_IDX = 3; // one in-state (green) donor per cluster
const CLUSTERS = HUBS.map((hub, ci) => ({
  hub,
  dots: SPOKES[ci].map(([a, r], i) => {
    const rad = (a * Math.PI) / 180;
    return {
      x: Math.round(hub.x + Math.cos(rad) * r),
      y: Math.round(hub.y + Math.sin(rad) * r),
      c: i === GREEN_IDX ? IN : OUT,
    };
  }),
}));

export default function OgImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
          background: '#0a0e13',
          // soft accent glow over a subtle top-to-bottom depth gradient
          backgroundImage:
            'radial-gradient(circle at 50% 18%, rgba(74,163,255,0.24), rgba(74,163,255,0) 58%),' +
            'linear-gradient(180deg, #0c1220 0%, #080b10 100%)',
        }}
      >
        {/* Money-flow beams (behind the content): donor states converging on a district. */}
        <svg width="1200" height="630" viewBox="0 0 1200 630" style={{ position: 'absolute', top: 0, left: 0 }}>
          {CLUSTERS.flatMap((cl, ci) => [
            ...cl.dots.map((d, i) => (
              <path
                key={`beam-${ci}-${i}`}
                d={`M ${d.x} ${d.y} L ${cl.hub.x} ${cl.hub.y}`}
                stroke={d.c}
                strokeWidth="1"
                fill="none"
                opacity="0.06"
              />
            )),
            ...cl.dots.map((d, i) => (
              <circle
                key={`dot-${ci}-${i}`}
                cx={d.x}
                cy={d.y}
                r={d.c === IN ? 6 : 5}
                fill={d.c}
                opacity={d.c === IN ? 0.4 : 0.18}
              />
            )),
            <circle key={`hub-${ci}`} cx={cl.hub.x} cy={cl.hub.y} r="9" fill={ACCENT} opacity="0.4" />,
          ])}
        </svg>

        {/* Central safe area (~80%): survives square (iMessage/Slack) and 2:1 (Twitter) crops. */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            textAlign: 'center',
            width: 1000,
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 96,
              height: 96,
              borderRadius: 22,
              background: ACCENT,
              color: '#05213f',
              fontSize: 60,
              fontWeight: 800,
              boxShadow: '0 0 60px rgba(74,163,255,0.55)',
            }}
          >
            $
          </div>

          <div
            style={{
              color: '#f2f6fb',
              fontSize: 92,
              fontWeight: 800,
              letterSpacing: -2,
              marginTop: 34,
              lineHeight: 1,
            }}
          >
            On The Money
          </div>

          <div style={{ color: '#9aa4b2', fontSize: 36, marginTop: 24, maxWidth: 860, lineHeight: 1.3 }}>
            An AI agent that answers U.S. House campaign-finance questions from real FEC
            filings, and maps the money.
          </div>

          <div style={{ display: 'flex', gap: 16, marginTop: 40 }}>
            {CHIPS.map((c) => (
              <div
                key={c}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: '12px 24px',
                  borderRadius: 999,
                  border: '1px solid rgba(74,163,255,0.35)',
                  background: 'rgba(74,163,255,0.08)',
                  color: '#cbd5e1',
                  fontSize: 27,
                  fontWeight: 600,
                }}
              >
                <div style={{ width: 11, height: 11, borderRadius: 999, background: ACCENT }} />
                {c}
              </div>
            ))}
          </div>

          <div style={{ color: ACCENT, fontSize: 28, fontWeight: 700, letterSpacing: 0.5, marginTop: 40 }}>
            onthemoney.fyi
          </div>
        </div>
      </div>
    ),
    { ...size },
  );
}
