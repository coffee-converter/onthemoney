import './globals.css';
import type { ReactNode } from 'react';
import type { Metadata, Viewport } from 'next';
import { Analytics } from '@vercel/analytics/react';

const DESCRIPTION =
  'An AI agent that answers your U.S. House campaign-finance questions from real FEC filings. Grounded, cited, calibrated, and mapped.';

export const viewport: Viewport = {
  themeColor: '#0d1117',
};

// Structured data: what this is, that it's free, and who built it.
const JSON_LD = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'WebSite',
      '@id': 'https://onthemoney.fyi/#website',
      url: 'https://onthemoney.fyi/',
      name: 'On The Money',
      description: DESCRIPTION,
      publisher: { '@id': 'https://onthemoney.fyi/#person' },
    },
    {
      '@type': 'WebApplication',
      name: 'On The Money',
      url: 'https://onthemoney.fyi/',
      applicationCategory: 'GovernmentApplication',
      operatingSystem: 'Web',
      description: DESCRIPTION,
      offers: { '@type': 'Offer', price: '0', priceCurrency: 'USD' },
      creator: { '@id': 'https://onthemoney.fyi/#person' },
    },
    {
      '@type': 'Person',
      '@id': 'https://onthemoney.fyi/#person',
      name: 'Aaron Hanson',
      url: 'https://aaronhanson.dev',
      sameAs: [
        'https://aaronhanson.dev',
        'https://github.com/coffee-converter',
        'https://www.linkedin.com/in/ildiscgolfer',
      ],
    },
  ],
};

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
          <a href="/" className="brand">
            <span className="brand-mark">$</span>
            <span className="brand-word">On The Money</span>
          </a>
          <div className="topnav-links">
            <a href="/">Atlas</a>
            <a href="/scoreboard">Scoreboard</a>
            <a href="/how-it-works">Under the hood</a>
            <span className="builtby">
              <span className="bb-prefix">Built by </span>
              <a href="https://aaronhanson.dev" target="_blank" rel="noopener noreferrer">
                Aaron Hanson
              </a>
            </span>
          </div>
        </nav>
        {children}
        <Analytics />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD) }}
        />
      </body>
    </html>
  );
}
