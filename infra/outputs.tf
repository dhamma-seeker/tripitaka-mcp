output "droplet_ip" {
  value       = digitalocean_droplet.server.ipv4_address
  description = "The public IP address of the Droplet"
}

output "droplet_ipv6" {
  value       = digitalocean_droplet.server.ipv6_address
  description = "IPv6 address"
}

output "droplet_urn" {
  value = digitalocean_droplet.server.urn
}

output "ssh_command" {
  value       = "ssh deploy@${digitalocean_droplet.server.ipv4_address}"
  description = "Command สำหรับ SSH เข้า droplet (ใช้ user deploy ไม่ใช่ root)"
}

output "next_steps" {
  value = <<-EOT

  ✓ Droplet พร้อมใช้งาน: ${digitalocean_droplet.server.ipv4_address}

  ขั้นตอนถัดไป:
    1. ssh deploy@${digitalocean_droplet.server.ipv4_address}
    2. cd /opt/tripitaka && git clone https://github.com/Ipurak/tripitaka-mcp.git .
    3. ./scripts/deploy.sh
    4. ตรวจ https://${var.domain_name}/health

  ⚠️  DNS: ตั้ง A record ของโดเมน → ${digitalocean_droplet.server.ipv4_address}
      (ถ้าใช้ Cloudflare: เปิด proxy (ส้ม) เพื่อซ่อน origin IP)
  EOT
}
