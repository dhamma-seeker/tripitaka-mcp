# This file handles the Domain record for api.tipitaka-mcp.com
# Use this ONLY after you have added your domain to DigitalOcean

resource "digitalocean_domain" "main" {
  name = var.domain_name
}

resource "digitalocean_record" "api" {
  domain = digitalocean_domain.main.id
  type   = "A"
  name   = "api"
  value  = digitalocean_droplet.server.ipv4_address
}
