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
does not touch DNS. The first passing drill (2026-11-02) took 65 minutes:
about 5 to create the droplet and run cloud-init, about 40 for `deploy.sh` to
download and restore the database dump and build its indexes, and the rest to build the
images. A real failover takes about as long before DNS can move. At about
$0.036 per hour for the `s-2vcpu-4gb` droplet, each drill costs a few cents.

The `ops-drill` workflow runs a drill on the 1st and 15th of every month (see
"Running from GitHub Actions" below). To run one from a laptop instead:

Requirements: VPN on (the DO firewall only allows SSH from
`ssh_allowed_cidrs`), a checkout with `infra/terraform.tfvars` and
`infra/backend.hcl`, and the R2 credentials exported as `AWS_ACCESS_KEY_ID`
and `AWS_SECRET_ACCESS_KEY`. The Terraform state lives in Cloudflare R2, so the
laptop and GitHub Actions see the same droplet.

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
For the same reason, the `https://<domain>/health → ok` line near the end of
the `deploy.sh` output reports the Oracle instance, not the drill droplet. The
script's own tests after it are the ones that check the droplet.
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

## Running from GitHub Actions

Four `workflow_dispatch` workflows do the same jobs without a laptop:

| Workflow | Does | Environment |
|---|---|---|
| `ops-drill` | a drill; also scheduled on the 1st and 15th | `standby` |
| `ops-failover` | builds the standby and keeps it (`--keep`); type `failover` to confirm | `production` |
| `ops-destroy` | destroys whatever the state holds; type `destroy` to confirm | `production` |
| `ops-deploy` | `git pull` + `deploy.sh` on the production server | `production` |

The Actions logs of a public repository are public. The workflows mask the
droplet IP, and the production address is a secret, so neither appears in the
log; read the standby IP from the DigitalOcean dashboard.

### One-time setup

1. Cloudflare > R2: create a bucket for the state (`tripitaka-tfstate` in the
   example) and an API token with Object Read & Write on that bucket only.
2. Copy `infra/backend.hcl.example` to `infra/backend.hcl` and fill in the
   account id. Export the R2 credentials, then move any local state into R2:

   ```bash
   cd infra && terraform init -migrate-state -backend-config=backend.hcl
   ```

3. In the repository settings, create two environments, both limited to the
   `main` branch: `standby` with no reviewers, and `production` with required
   reviewers. Limiting them to `main` keeps the secrets away from workflows
   pushed on other branches.
4. Add these secrets to both environments:

   | Secret | Value |
   |---|---|
   | `DO_TOKEN` | DigitalOcean token with write access |
   | `DEPLOY_SSH_KEY` | private key of the `deploy` user |
   | `PROD_ENV` | the production `.env` |
   | `TF_BACKEND_HCL` | contents of `infra/backend.hcl` |
   | `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` | the R2 token |

   And to `production` only:

   | Secret | Value |
   |---|---|
   | `PROD_HOST` | the production server address |
   | `PROD_KNOWN_HOSTS` | `ssh-keyscan -t ed25519 <PROD_HOST>` output |

When `.env` changes on the server, update `PROD_ENV` in both environments as
well as the password manager copy.

A drill that is cancelled or times out cannot destroy its droplet. The next
drill then stops at preflight with "terraform state ยังมีทรัพยากรอยู่"; run
`ops-destroy` to clear it.

## Keeping the standby account usable

- The DO API token (in `infra/terraform.tfvars` and the `DO_TOKEN` secret)
  needs write access. If you created it with an expiry, renew it in both places
  before then; a drill fails fast at `terraform apply` if it has expired.
- Keep a payment method on the DO account. A billing alert at a few dollars
  (Billing > Billing Alerts) catches a droplet that a failed destroy left
  running.
- When the VPN's exit IP changes, update `ssh_allowed_cidrs` in
  `terraform.tfvars`.
