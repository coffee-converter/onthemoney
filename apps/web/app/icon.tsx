import { ImageResponse } from 'next/og';

// Generated favicon (no binary asset needed). Next wires this into <link rel="icon">.
export const size = { width: 64, height: 64 };
export const contentType = 'image/png';

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#4aa3ff',
          color: '#05213f',
          fontSize: 46,
          fontWeight: 800,
        }}
      >
        $
      </div>
    ),
    { ...size },
  );
}
