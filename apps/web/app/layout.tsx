import './globals.css';
import type { ReactNode } from 'react';
import type { Metadata } from 'next';
import { Analytics } from '@vercel/analytics/react';

const DESCRIPTION =
  'Ask a plain-English question about U.S. House campaign finance. An AI agent resolves it against real FEC filings — grounded, cited, and calibrated — and draws the money on a live map.';

export const metadata: Metadata = {
  metadataBase: new URL('https://onthemoney.fyi'),
  title: {
    default: 'On The Money — U.S. House campaign finance atlas',
    template: '%s · On The Money',
  },
  description: DESCRIPTION,
  applicationName: 'On The Money',
  keywords: [
    'campaign finance',
    'FEC filings',
    'U.S. House of Representatives',
    'political donations',
    'money in politics',
    'election data',
    'donor geography',
  ],
  alternates: { canonical: '/' },
  openGraph: {
    type: 'website',
    url: 'https://onthemoney.fyi',
    siteName: 'On The Money',
    title: 'On The Money — U.S. House campaign finance atlas',
    description: DESCRIPTION,
  },
  twitter: {
    card: 'summary_large_image',
    title: 'On The Money — U.S. House campaign finance atlas',
    description: DESCRIPTION,
  },
  robots: { index: true, follow: true },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav className="topnav">
          <a href="/" className="brand">On The Money</a>
          <div className="topnav-links">
            <a href="/">Atlas</a>
            <a href="/scoreboard">Scoreboard</a>
            <a href="/how-it-works">Under the hood</a>
          </div>
        </nav>
        {children}
        <Analytics />
      </body>
    </html>
  );
}
