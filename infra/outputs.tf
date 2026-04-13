output "droplet_ip" {
  value       = digitalocean_droplet.server.ipv4_address
  description = "The public IP address of the Droplet"
}

output "droplet_urn" {
  value = digitalocean_droplet.server.urn
}
