# Running on Oracle Cloud (Always Free) and moving off another VPS

This runbook covers two things: creating an Oracle Cloud Infrastructure (OCI)
Always Free Ampere A1 instance for this stack, and moving a running instance
from another VPS (for example a DigitalOcean droplet built from `infra/`) onto
it with almost no downtime. The general deploy flow in
[`DEPLOYMENT.md`](../DEPLOYMENT.md) still applies; this file only covers what
differs on OCI and the cutover itself.

## Before you start

Always Free compute exists only in your tenancy's home region, which you pick
at sign-up and cannot change. Every resource below goes in that region.

The free Ampere allowance is 4 OCPU and 24 GB RAM in total, plus 200 GB of
block storage. One `VM.Standard.A1.Flex` instance using all of it is far more
than this stack needs (it ran on 2 vCPU / 4 GB, see
[`CAPACITY.md`](CAPACITY.md)).

Two account behaviours affect a small, mostly idle server like this one:

- Popular regions often return "Out of capacity" when you create an A1
  instance. Try each availability domain in turn, or retry later.
- Oracle may reclaim Always Free instances that stay idle (low CPU, network
  and memory use) for 7 days.

Upgrading the account to Pay As You Go solves both: A1 capacity is easier to
get and idle reclamation no longer applies. Usage inside the Always Free limits
stays free after the upgrade. Set a budget alert (Billing > Budgets) at a small
amount so anything outside the free limits shows up quickly.

## 1. Network

Use Networking > Virtual cloud networks > Start VCN Wizard > "Create VCN with
Internet Connectivity". The defaults are fine.

Then open the public subnet's security list and add ingress rules:

| Source | Protocol | Port | Purpose |
|---|---|---|---|
| `0.0.0.0/0` | TCP | 80 | HTTP, ACME challenges |
| `0.0.0.0/0` | TCP | 443 | HTTPS |
| `0.0.0.0/0` | UDP | 443 | HTTP/3 |

The wizard already allows TCP 22 from anywhere. Narrow it to your own IP
(`curl ifconfig.me`) the same way `ssh_allowed_cidrs` does in the Terraform.

If Cloudflare proxies your domain, you can limit 80 and 443 to
[Cloudflare's IP ranges](https://www.cloudflare.com/ips/) instead of
`0.0.0.0/0`. Do that after the cutover works, not before.

## 2. Render the cloud-init script

[`infra/cloud-init.yml`](../infra/cloud-init.yml) is a Terraform template.
Without Terraform, render it on your laptop with the deploy public key:

```bash
./scripts/render-cloud-init.sh ~/.ssh/tripitaka_prod.pub > /tmp/cloud-init.yml
```

The script refuses anything that is not a `.pub` file. Use the same key as on
the old server if you want `ssh deploy@...` to keep working unchanged.

On OCI's Ubuntu images, cloud-init also removes Oracle's default iptables rules
(`/etc/iptables/rules.v4`). Those rules reject every inbound port except 22,
so without this step 80 and 443 stay closed even with the security list open.
UFW manages the host firewall afterwards, as on DigitalOcean.

## 3. Create the instance

Compute > Instances > Create instance:

- Shape: Ampere, `VM.Standard.A1.Flex`, 4 OCPU, 24 GB. Pick the shape before
  the image: the image list only offers aarch64 builds once an Ampere shape is
  selected. The OCPU and memory fields are inside the expanded shape row.
- Image: Canonical Ubuntu 24.04 (the aarch64 build). This is the tested
  combination; 22.04 also works but leaves standard support in April 2027.
  Not Oracle Linux: the cloud-init script assumes Ubuntu (apt, ufw, the `ssh`
  unit).
- Networking: the public subnet from step 1, with a public IPv4 address.
- SSH keys: paste the same public key. OCI installs it for the `ubuntu` user,
  but the hardening in cloud-init only allows `deploy` to log in, so you will
  use `deploy`.
- Boot volume: set a custom size of 100 GB or more. The app image is about
  9 GB and `deploy.sh` keeps three versions.
- Advanced options > Management > cloud-init script: paste or upload the
  rendered file.

Cloud-init takes a few minutes after the instance shows Running. Check it:

```bash
ssh deploy@<OCI_IP> 'cloud-init status --wait && cat /var/log/tripitaka-bootstrap.log'
```

Optionally convert the ephemeral public IP to a reserved one (instance > VNIC >
IPv4 addresses) so it survives if the instance is ever recreated.

## 4. Copy state from the old server

Most state is rebuilt by `deploy.sh`: the database comes from the Hugging Face
dump and the images are built from source. Two things are worth copying.

`.env` holds the domain, CORS origins and the rest of your configuration.
Copying it keeps them identical. The database passwords in it only matter to
the new database, which is created fresh with whatever `.env` says.

The `caddy_data` volume holds the TLS certificates and ACME account. With it,
the new server serves valid certificates the moment DNS points at it. Without
it, Caddy has to obtain new certificates after the cutover, and HTTPS fails
until it does.

On the old server (the volume name is `<project>_caddy_data`; check with
`docker volume ls`):

```bash
cd /opt/tripitaka
docker run --rm -v tripitaka_caddy_data:/data -v "$PWD":/backup alpine \
    tar czf /backup/caddy_data.tgz -C /data .
```

Move both files through your laptop (the servers have no keys for each other):

```bash
scp deploy@<OLD_IP>:/opt/tripitaka/{.env,caddy_data.tgz} /tmp/
scp /tmp/.env /tmp/caddy_data.tgz deploy@<OCI_IP>:/opt/tripitaka/
rm /tmp/.env /tmp/caddy_data.tgz
```

On the new server, restore the volume before the first deploy:

```bash
cd /opt/tripitaka
chmod 600 .env
docker volume create tripitaka_caddy_data
docker run --rm -v tripitaka_caddy_data:/data -v "$PWD":/backup alpine \
    tar xzf /backup/caddy_data.tgz -C /data
rm caddy_data.tgz
```

Compose prints a warning that the volume was not created by Compose. It uses
the volume anyway.

## 5. Deploy

Check which branch the old server runs (`git -C /opt/tripitaka rev-parse
--abbrev-ref HEAD`) and deploy the same one:

```bash
cd /opt/tripitaka
git clone <REPO_URL> /tmp/repo && mv /tmp/repo/.git . && git checkout -f <BRANCH>
./scripts/deploy.sh
```

The clone goes through `/tmp` because `/opt/tripitaka` already holds `.env`,
and `git clone` refuses a non-empty directory.

All images used here (`python:3.12-slim`, `ankane/pgvector`, `caddy`) publish
arm64 builds, so nothing in the Dockerfiles or compose file changes. The first
build is slow: PyTorch's Linux wheels pull in the NVIDIA CUDA libraries on
arm64 as well, so the dependency layer is still about 5.5 GB.

## 6. Test before touching DNS

From your laptop, send requests to the new IP with the real hostname:

```bash
curl -sS --resolve mcp.example.org:443:<OCI_IP> https://mcp.example.org/health
curl -sS --resolve example.org:443:<OCI_IP> -o /dev/null -w '%{http_code}\n' https://example.org/read/healthz
```

With the copied `caddy_data` these succeed without `-k`. To try the MCP tools
themselves before the cutover, add `<OCI_IP> mcp.example.org` to your laptop's
`/etc/hosts`, connect a client, and remove the line afterwards.
`scripts/smoke_test.sh` resolves the hostname through DNS, so run it after the
cutover.

## 7. Cut over

1. In your DNS provider, change the A records (MCP host, apex, `www`) to the
   OCI IP. Remove any AAAA records that point at the old server, since the new
   instance has no IPv6 unless you add it.
2. Run `./scripts/smoke_test.sh mcp.example.org` once `dig` returns the new
   IP (or Cloudflare's IPs, if proxied).
3. Watch both servers' Caddy logs (`docker logs -f tripitaka-caddy`). Traffic
   moves to the new one within a few minutes with Cloudflare proxying, longer
   with plain DNS as old TTLs expire.
4. Move scheduled jobs. Check `crontab -l` on the old server (for example the
   `scripts/backup.sh` job) and set the same up on the new one. See
   "Backups on OCI" below for the AWS CLI and PATH details.

## Backups on OCI

`scripts/backup.sh` uploads with the AWS CLI. Ubuntu 24.04 no longer ships
`awscli` in apt, so install the snap:

```bash
sudo snap install aws-cli --classic
```

The snap lives in `/snap/bin`, which is not on cron's default PATH. Put a
`PATH=` line at the top of the deploy user's crontab, or the job stops with
"aws CLI ไม่พบ":

```
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin
0 3 * * * /opt/tripitaka/scripts/backup.sh >> /var/log/tripitaka-backup.log 2>&1
0 4 * * 0 docker builder prune -af --filter until=168h >> /var/log/tripitaka-prune.log 2>&1
```

To test the job the way cron runs it:

```bash
env -i HOME=$HOME PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin \
    /opt/tripitaka/scripts/backup.sh
```

OCI Object Storage can replace another provider's bucket. Always Free
includes 10 GB of Standard storage (plus 10 GB of Archive), enough for 7 daily
dumps of about 800 MB. Turn on "Uncommitted multipart uploads cleanup" when
creating the bucket, so an interrupted upload does not keep using that quota.
It needs a bucket
and a Customer Secret Key (Profile > User settings > Customer secret keys),
which is an S3-style access key and secret. The `DO_SPACES_*` variables in
`.env` then become:

| Variable | Value |
|---|---|
| `DO_SPACES_BUCKET` | the bucket name |
| `DO_SPACES_REGION` | the region id, e.g. `eu-frankfurt-1` |
| `DO_SPACES_ENDPOINT` | `https://<namespace>.compat.objectstorage.<region>.oraclecloud.com` |
| `DO_SPACES_KEY` | the Customer Secret Key's access key |
| `DO_SPACES_SECRET` | the secret, shown once when the key is created |

The namespace is on the bucket's details page and under Tenancy details.

## 8. Retire the old server

Leave the old server running for about a week in case you need to switch DNS
back. Then, for the DigitalOcean Terraform:

```bash
cd infra
terraform plan -destroy   # read the list before confirming
terraform destroy
```

`terraform plan -destroy` shows everything Terraform will remove, including the
firewall, project and any DNS records it manages. Take a final `pg_dump` first
if the old database holds anything the Hugging Face dump does not.
