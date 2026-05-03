# site/

Static landing page served by Caddy at the apex domain (`tripitaka-mcp.com`).
Mounted read-only into the Caddy container at `/var/www/site/` via
`docker-compose.prod.yml`. No build step — single HTML file with embedded CSS.

## Files

- `index.html` — landing page (Schema.org JSON-LD, Open Graph, Twitter Card meta)
- `favicon.svg` — minimal "T" mark in project gold
- `og-image.svg` — source-of-truth for the social card image
- `og-image.png` — 1200×630 PNG rendered from the SVG (used by Open Graph / Twitter)
- `robots.txt` — allow all + sitemap pointer
- `sitemap.xml` — apex URLs (search engines crawl /topics on `mcp.*` from the homepage link)
- `.well-known/security.txt` — vulnerability disclosure → GitHub Issues

## Regenerating `og-image.png`

After editing `og-image.svg`, regenerate the PNG (most social platforms don't accept SVG):

```bash
rsvg-convert -w 1200 -h 630 -f png -o site/og-image.png site/og-image.svg
```

Requires `librsvg` (`brew install librsvg` on macOS). Commit both `og-image.svg`
and `og-image.png` together.

## Deploying changes

The `site/` directory is bind-mounted into the Caddy container, so on the
production droplet:

```bash
git pull origin main
# no Caddy restart needed for static files — Caddy file_server reads from disk
```

Caddyfile changes do require `docker compose ... restart caddy`.
