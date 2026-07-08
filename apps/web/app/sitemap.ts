import type { MetadataRoute } from 'next';

const BASE = 'https://onthemoney.fyi';

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: `${BASE}/`, changeFrequency: 'weekly', priority: 1 },
    { url: `${BASE}/scoreboard`, changeFrequency: 'weekly', priority: 0.7 },
    { url: `${BASE}/how-it-works`, changeFrequency: 'monthly', priority: 0.6 },
  ];
}
