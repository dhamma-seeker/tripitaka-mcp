# =============================================================================
# Tripitaka MCP — Droplet + Firewall + Project + Domain
# =============================================================================

# 1. SSH Key (ลงทะเบียน public key สู่ DO)
resource "digitalocean_ssh_key" "main" {
  name       = var.ssh_key_name
  public_key = file(var.public_key_path)
}

# 2. Droplet (VPS) — Ubuntu 22.04 พร้อม cloud-init bootstrap
#    cloud-init.yml ทำ: สร้าง deploy user, ufw, fail2ban, Docker, swap
resource "digitalocean_droplet" "server" {
  image    = "ubuntu-22-04-x64"
  name     = "tripitaka-mcp-server"
  region   = var.region
  size     = var.droplet_size
  ssh_keys = [digitalocean_ssh_key.main.id]

  # Enable monitoring agent + IPv6
  monitoring = true
  ipv6       = true

  user_data = templatefile("${path.module}/cloud-init.yml", {
    deploy_public_key = trimspace(file(var.public_key_path))
  })

  # Cloud-init ใช้เวลาประมาณ 2-3 นาที — รอให้เสร็จก่อน terraform คืน success
  provisioner "remote-exec" {
    inline = [
      "cloud-init status --wait",
      "echo '✓ cloud-init finished'",
    ]
    connection {
      type        = "ssh"
      host        = self.ipv4_address
      user        = "deploy"
      private_key = file(replace(var.public_key_path, ".pub", ""))
      timeout     = "10m"
    }
  }
}

# 3. Project (รวมทรัพยากรเข้าโปรเจกต์เดียวใน DO dashboard)
resource "digitalocean_project" "main" {
  name        = "Tripitaka MCP"
  description = "A server for the Tripitaka Model Context Protocol"
  purpose     = "Service or API"
  environment = "Production"
  resources   = [digitalocean_droplet.server.urn]
}

# 4. Firewall (ชั้น DO — เสริมกับ ufw บน host)
#    แนะนำให้ผ่าน Cloudflare proxy อีกชั้น (กรอง IP ระดับ edge)
resource "digitalocean_firewall" "main" {
  name = "tripitaka-mcp-firewall"

  droplet_ids = [digitalocean_droplet.server.id]

  # --- Inbound ---------------------------------------------------------------
  # SSH — ถ้าอยาก restrict ให้เปลี่ยน source_addresses เป็น IP ของคุณ
  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = var.ssh_allowed_cidrs
  }

  # HTTP — Caddy จะ redirect → 443
  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # HTTPS
  inbound_rule {
    protocol         = "tcp"
    port_range       = "443"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # HTTP/3 (QUIC)
  inbound_rule {
    protocol         = "udp"
    port_range       = "443"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # --- Outbound --------------------------------------------------------------
  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "icmp"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}
