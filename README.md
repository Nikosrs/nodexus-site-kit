# nodexus-site-kit

Small, dependency-free building blocks for shipping fast, secure static brochure sites (restaurants, shops, law firms, garages…) on a single VPS.

Extracted from real client projects. Everything is plain files: no framework, no build step beyond a shell script.

## What's inside

| Path | What it does |
|---|---|
| `docker/Dockerfile` | Two-stage build: fingerprints assets, then serves them with nginx. Includes a healthcheck. |
| `docker/fingerprint.sh` | Renames images, fonts, CSS and JS with a content hash and rewrites every reference, so files can be cached for a year. Fails the build on any broken local reference. |
| `docker/nginx.conf` | Gzip, long immutable cache for hashed files, revalidation for pages, custom 404, and `noindex` on every host except the real domain (staging URLs never get indexed). |
| `docker/security.inc` | Security headers: strict CSP, `nosniff`, frame and referrer policies, permissions policy. |
| `contact-service/` | ~100-line contact form relay (Python standard library only): SMTP, honeypot, input validation, per-IP rate limit, no data stored. |
| `scripts/lighthouse.sh` | Mobile Lighthouse audit with pass/fail targets (perf ≥ 90, a11y / best practices / SEO ≥ 95). |
| `pages/` | `404.html`, `mentions-legales.html` (French legal notice), `robots.txt`, `sitemap.xml` with `{{PLACEHOLDERS}}`. |

## Quick start

Expected site layout:

```
site/            index.html, styles.css, script.js, images/, fonts/
build/           fingerprint.sh, security.inc   (from docker/)
nginx.conf       (from docker/, set your domain in the map block)
Dockerfile       (from docker/)
```

```sh
docker build -t my-site .
docker run --rm -p 8080:80 my-site
./scripts/lighthouse.sh http://localhost:8080
```

Contact service:

```sh
docker build -t contact contact-service
docker run --rm -p 8081:8080 \
  -e SMTP_HOST=smtp.example.com -e SMTP_USER=forms@example.com -e SMTP_PASS=... \
  -e CONTACT_TO=owner@example.com -e SITE_NAME="Example" contact
```

Never commit `SMTP_PASS`: set it in your host's environment settings.

## Notes

- The legal-notice template follows French law (mentions légales); adapt it for other countries.
- The CSP in `security.inc` is deliberately strict (`default-src 'none'`). Loosen it only for what the site really loads.

## License

MIT, see [LICENSE](LICENSE).
