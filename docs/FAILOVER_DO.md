# Failover to DigitalOcean

Production runs on one Oracle Cloud instance (see
[`ORACLE_CLOUD.md`](ORACLE_CLOUD.md)). DigitalOcean is the cold standby: the
DO account stays open, but nothing runs or is stored there, so it costs
nothing until it is used. When Oracle is down for longer than you are willing
to wait, `scripts/failover-drill.sh --keep` builds a replacement on DO from the
repo, and DNS moves to it.

Everything the server needs can be rebuilt except `.env`:

| Piece | Where it comes from |
|---|---|
| Server | `infra/` Terraform + `infra/cloud-init.yml` |
| Code | GitHub |
| Database | the dump on Hugging Face, restored by `deploy.sh` |
| TLS certificates | Caddy requests new ones once DNS points at the server |
| `.env` | your password manager copy |

The OCI bucket backups are not part of this plan: if the Oracle account is the
problem, they are out of reach too.

## What keeps the standby from drifting

Production gets changed and the standby does not, so the standby slowly stops
working unless something checks it. These run without anyone remembering to:

- `infra/cloud-init.yml` does all host setup, including the AWS CLI and the
  cron jobs (`/etc/cron.d/tripitaka`). Nothing is set up by hand on one host
  only. If you find yourself running a setup command on the Oracle host, add
  it to cloud-init in the same change.
- Both hosts run the same Ubuntu release (`droplet_image` in
  `infra/variables.tf`). Upgrade them together.
- `deploy.sh` stops if `.env` lacks a key that `.env.example` requires, and
  warns about keys `.env.example` does not mention. Add every new variable to
  `.env.example`, then update the password manager copy.
- `.github/workflows/ci.yml` builds the images for amd64 (DO) and arm64
  (Oracle) on every pull request and once a month from scratch, and validates
  the Terraform, compose file and cloud-init.
- `.github/workflows/do-standby.yml` checks monthly that DO still offers the
  image, size and region Terraform asks for. It needs a read-only DO token in
  the repository secret `DO_READ_TOKEN`.

None of these prove the standby actually comes up. The drill does.

## Drill (twice a month)

A drill builds the standby, deploys, tests it over SSH and destroys it. It
does not touch DNS. Expect well under an hour at about $0.036 per hour for the
`s-2vcpu-4gb` droplet.

Requirements: VPN on (the DO firewall only allows SSH from
`ssh_allowed_cidrs`), and the checkout that holds `infra/terraform.tfvars` and
the Terraform state.

1. Export `.env` from the password manager to a temporary file, for example
   `~/tripitaka-drill.env`.
2. Run:

   ```bash
   ./scripts/failover-drill.sh --env-file ~/tripitaka-drill.env
   ```

3. Delete the temporary file.

The script refuses to start if the Terraform state still holds resources, and
destroys the droplet on exit even when a step fails. Each run appends its
result and duration to `infra/.drill-history`.

On the drill droplet Caddy cannot get certificates, because the domain still
points at Oracle; the certificate step is only exercised in a real failover.
The script also removes the drill droplet's backup cron job so it does not
upload to the production bucket.

If a drill fails, fix the cause in the repo before the next one. The failure
is the point of the drill: it found something a real failover would have hit.

## Real failover

1. Decide. A few minutes of Oracle trouble is cheaper to wait out than a DNS
   move; check the [OCI status page](https://ocistatus.oraclecloud.com/) and
   the instance in the console first.
2. Turn on the VPN, export `.env` from the password manager, and run:

   ```bash
   ./scripts/failover-drill.sh --env-file ~/tripitaka-drill.env --keep
   ```

   With `--keep` the droplet stays up if every test passes. The script prints
   its IP.
3. The nightly backup job stays in place in `--keep` mode and uploads to the
   bucket named in `.env`. If the Oracle account itself is unavailable, those
   uploads fail until it returns. The database can always be restored from
   Hugging Face, so this can wait.
4. In Cloudflare, point the A records for the apex, `mcp` and `www` at the DO
   IP. Leave the proxy on.
5. Within a few minutes Caddy obtains certificates. Then run:

   ```bash
   ./scripts/smoke_test.sh mcp.tripitaka-mcp.com
   ```

6. Delete the temporary `.env` file.

## Failing back to Oracle

1. Once the Oracle instance is healthy (`/health` through
   `curl --resolve mcp.tripitaka-mcp.com:443:<OCI_IP>`), point the Cloudflare
   A records back at the Oracle IP.
2. Watch `docker logs -f tripitaka-caddy` on the DO droplet until requests
   stop arriving.
3. Destroy the droplet:

   ```bash
   cd infra && terraform plan -destroy && terraform destroy
   ```

4. Check DO billing a day later to confirm nothing is left running.

## Keeping the standby account usable

- The DO API token in `infra/terraform.tfvars` needs write access. If you
  created it with an expiry, renew it before then; a drill fails fast at
  `terraform apply` if it has expired.
- Keep a payment method on the DO account. A billing alert at a few dollars
  (Billing > Billing Alerts) catches a droplet that a failed destroy left
  running.
- When the VPN's exit IP changes, update `ssh_allowed_cidrs` in
  `terraform.tfvars`.
