import { clientIp, sanitizeQuery } from './request';

describe('sanitizeQuery', () => {
  it('rejects non-strings and empty input', () => {
    expect(() => sanitizeQuery(42)).toThrow();
    expect(() => sanitizeQuery('   ')).toThrow();
  });

  it('trims and caps length', () => {
    expect(sanitizeQuery('  hi  ')).toBe('hi');
    expect(sanitizeQuery('x'.repeat(600))).toHaveLength(500);
  });
});

describe('clientIp', () => {
  const SECRET = 'edge-secret';

  it('trusts x-otm-real-ip when the edge stamp matches, over Fly-Client-IP', () => {
    const ip = clientIp(
      { 'x-otm-edge-secret': SECRET, 'x-otm-real-ip': '1.2.3.4', 'fly-client-ip': '9.9.9.9' },
      SECRET,
    );
    expect(ip).toBe('1.2.3.4');
  });

  it('ignores a forged x-otm-real-ip when the stamp is wrong or missing', () => {
    // A direct caller to the public BFF can set these headers but not the secret.
    expect(
      clientIp({ 'x-otm-edge-secret': 'guess', 'x-otm-real-ip': '6.6.6.6', 'fly-client-ip': '9.9.9.9' }, SECRET),
    ).toBe('9.9.9.9');
    expect(
      clientIp({ 'x-otm-real-ip': '6.6.6.6', 'fly-client-ip': '9.9.9.9' }, SECRET),
    ).toBe('9.9.9.9');
  });

  it('never trusts the real-ip header when no edge secret is configured', () => {
    expect(
      clientIp({ 'x-otm-edge-secret': '', 'x-otm-real-ip': '6.6.6.6', 'fly-client-ip': '9.9.9.9' }, undefined),
    ).toBe('9.9.9.9');
  });

  it('falls back to Fly-Client-IP, then the first X-Forwarded-For hop', () => {
    expect(clientIp({ 'fly-client-ip': '9.9.9.9' }, SECRET)).toBe('9.9.9.9');
    expect(clientIp({ 'x-forwarded-for': '5.5.5.5, 8.8.8.8' }, SECRET)).toBe('5.5.5.5');
    expect(clientIp({}, SECRET)).toBeUndefined();
  });
});
