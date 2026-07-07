import { ImageResponse } from 'next/og';

// Generated social-share image (1200x630). Next wires this into og:image/twitter:image.
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';
export const alt = 'On The Money — U.S. House campaign finance atlas';

const ACCENT = '#4aa3ff';
const CHIPS = ['Grounded', 'Cited', 'Calibrated'];

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
          background: '#0a0e13',
          // soft accent glow over a subtle top-to-bottom depth gradient
          backgroundImage:
            'radial-gradient(circle at 50% 18%, rgba(74,163,255,0.24), rgba(74,163,255,0) 58%),' +
            'linear-gradient(180deg, #0c1220 0%, #080b10 100%)',
        }}
      >
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

          <div style={{ color: '#9aa4b2', fontSize: 35, marginTop: 24, maxWidth: 880, lineHeight: 1.3 }}>
            Ask about U.S. House campaign finance. An AI agent resolves it against real FEC
            filings — then draws the money on a live map.
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
