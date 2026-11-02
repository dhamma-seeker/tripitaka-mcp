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

  เครื่องนี้เป็นเครื่องสำรองของ Oracle · ปกติ scripts/failover-drill.sh
  วาง .env, deploy และทดสอบให้ต่อจากนี้ ถ้าทำเองดู docs/FAILOVER_DO.md

  ⚠️  failover จริง: ชี้ A record (apex, mcp, www) ใน Cloudflare → ${digitalocean_droplet.server.ipv4_address}
      เปิด proxy ไว้ แล้วรัน scripts/smoke_test.sh
  EOT
}
