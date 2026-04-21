variable "do_token" {
  description = "DigitalOcean Personal Access Token"
  type        = string
  sensitive   = true
}

variable "region" {
  description = "DigitalOcean region"
  type        = string
  default     = "sgp1"
}

variable "droplet_size" {
  description = "Droplet size"
  type        = string
  default     = "s-2vcpu-4gb"
}

variable "ssh_key_name" {
  description = "Name for the SSH key in DigitalOcean"
  type        = string
  default     = "tripitaka-mcp-key"
}

variable "public_key_path" {
  description = "Local path to the SSH public key"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "domain_name" {
  description = "Root domain name — override ใน terraform.tfvars"
  type        = string
  default     = "example.com"
}

variable "ssh_allowed_cidrs" {
  description = "CIDR blocks ที่ได้รับอนุญาตให้ SSH เข้า droplet (แนะนำระบุ IP ของคุณ)"
  type        = list(string)
  default     = ["0.0.0.0/0", "::/0"]
}
