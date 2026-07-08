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
const HUB = { x: 600, y: 315 };
const BEAMS = [
  { x: 95, y: 250, c: IN }, // left: the district's own (in-state) money
  { x: 1105, y: 385, c: OUT }, // right: out-of-state money
];

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
          {BEAMS.map((b, i) => (
            <path
              key={`beam-${i}`}
              d={`M ${b.x} ${b.y} L ${HUB.x} ${HUB.y}`}
              stroke={b.c}
              strokeWidth="1.5"
              fill="none"
              opacity="0.1"
            />
          ))}
          {BEAMS.map((b, i) => (
            <circle
              key={`dot-${i}`}
              cx={b.x}
              cy={b.y}
              r={b.c === IN ? 8 : 6}
              fill={b.c}
              opacity={b.c === IN ? 0.6 : 0.3}
            />
          ))}
          <circle cx={HUB.x} cy={HUB.y} r="6" fill={ACCENT} opacity="0.45" />
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
