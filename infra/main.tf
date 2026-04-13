# 1. SSH Key
resource "digitalocean_ssh_key" "main" {
  name       = var.ssh_key_name
  public_key = file(var.public_key_path)
}

# 2. Droplet (VPS)
resource "digitalocean_droplet" "server" {
  image    = "ubuntu-22-04-x64"
  name     = "tripitaka-mcp-server"
  region   = var.region
  size     = var.droplet_size
  ssh_keys = [digitalocean_ssh_key.main.id]

  # Bootstrap: Install Docker and Docker Compose
  user_data = <<-EOF
              #!/bin/bash
              apt-get update
              apt-get install -y apt-transport-https ca-certificates curl software-properties-common
              curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
              add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
              apt-get update
              apt-get install -y docker-ce docker-compose-plugin
              systemctl enable docker
              systemctl start docker
              EOF
}

# 3. Project (to keep things organized)
resource "digitalocean_project" "main" {
  name        = "Tripitaka MCP"
  description = "A server for the Tripitaka Model Context Protocol"
  purpose     = "Service or API"
  environment = "Production"
  resources   = [digitalocean_droplet.server.urn]
}

# 4. Firewall
resource "digitalocean_firewall" "main" {
  name = "tripitaka-mcp-firewall"

  droplet_ids = [digitalocean_droplet.server.id]

  # Inbound Rules
  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "8080"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # Outbound Rules (Allow everything)
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
