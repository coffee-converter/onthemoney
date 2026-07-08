import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Page not found',
  robots: { index: false, follow: false },
};

export default function NotFound() {
  return (
    <main className="notice">
      <div className="notice-code">404</div>
      <h1>We couldn&apos;t find that page</h1>
      <p>
        The page you&apos;re looking for doesn&apos;t exist or has moved. Head back to the
        atlas and ask a campaign-finance question instead.
      </p>
      <div className="notice-actions">
        <a href="/" className="notice-btn primary">
          Back to the atlas
        </a>
        <a href="/how-it-works" className="notice-btn">
          Under the hood
        </a>
      </div>
    </main>
  );
}
