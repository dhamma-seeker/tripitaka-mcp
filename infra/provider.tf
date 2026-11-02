terraform {
  # use_lockfile ใน backend s3 ต้องการ Terraform 1.10 ขึ้นไป
  required_version = ">= 1.10"

  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }

  # State อยู่ใน Cloudflare R2 (S3-compatible) เพื่อให้ทั้ง laptop และ GitHub Actions
  # เห็นเครื่องสำรองชุดเดียวกัน · ห้ามย้ายไปไว้บน Oracle: วันที่ Oracle ล่มคือวันที่ต้องใช้ state
  # ค่าจริงอยู่ใน backend.hcl (gitignored) ดู backend.hcl.example
  #   terraform init -backend-config=backend.hcl
  backend "s3" {}
}

provider "digitalocean" {
  token = var.do_token
}
