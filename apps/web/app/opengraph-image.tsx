import { ImageResponse } from 'next/og';

// Generated social-share image (1200x630). Next wires this into og:image/twitter:image.
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';
export const alt = 'On The Money — U.S. House campaign finance atlas';

export default function OgImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          background: '#0d1117',
          padding: '0 90px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 22 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 66,
              height: 66,
              borderRadius: 15,
              background: '#4aa3ff',
              color: '#05213f',
              fontSize: 44,
              fontWeight: 800,
            }}
          >
            $
          </div>
          <div style={{ color: '#4aa3ff', fontSize: 30, fontWeight: 700 }}>onthemoney.fyi</div>
        </div>
        <div style={{ color: '#e6edf3', fontSize: 84, fontWeight: 800, marginTop: 28, lineHeight: 1.05 }}>
          On The Money
        </div>
        <div style={{ color: '#9aa4b2', fontSize: 36, marginTop: 22, maxWidth: 980, lineHeight: 1.3 }}>
          U.S. House campaign finance, answered from the record — grounded, cited, and drawn on a live map.
        </div>
      </div>
    ),
    { ...size },
  );
}
