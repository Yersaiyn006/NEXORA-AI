# NEXORA AI — Oracle Cloud Always Free

1. Create an **Always Free eligible** Ubuntu 24.04 ARM64 Ampere A1 VM (maximum total 2 OCPU / 12 GB RAM on an Always Free tenancy). Choose a public IPv4 address and SSH key. Keep within free storage quotas.
2. In Oracle VCN security list / NSG allow TCP 80 and 443 from 0.0.0.0/0; restrict TCP 22 to your own IP. On Ubuntu configure UFW consistently with the OCI network rules. Never expose PostgreSQL port 5432 or Gunicorn port 8000.
3. Point your domain's DNS A record to the VM's public IP. A domain is needed for automatic trusted HTTPS; Oracle does not automatically provide a free custom domain.
4. Connect via SSH and install Docker Engine + Docker Compose plugin from Docker's official Ubuntu instructions. Verify `docker compose version`.
5. `git clone <YOUR_REPOSITORY_URL> nexora && cd nexora` (or pull into existing checkout). Copy these patch files into the same paths. Do not upload `.env` to GitHub.
6. `cp .env.oracle.example .env` and edit `.env` with your domain and random passwords. Generate secrets with `python3 -c 'import secrets; print(secrets.token_urlsafe(48))'` (run separately for both). Never share keys in chat.
7. `docker compose -f compose.oracle.yml up -d --build`
8. `docker compose -f compose.oracle.yml exec web python manage.py migrate --noinput`
9. `docker compose -f compose.oracle.yml exec web python manage.py check --deploy`
10. `docker compose -f compose.oracle.yml logs --tail=100 caddy web` and open https://YOUR_DOMAIN
11. To create an admin: `docker compose -f compose.oracle.yml exec web python manage.py createsuperuser`.

## Updates
`git pull && docker compose -f compose.oracle.yml up -d --build && docker compose -f compose.oracle.yml exec web python manage.py migrate --noinput`

## Backup (store copies off the VM)
`docker compose -f compose.oracle.yml exec -T db pg_dump -U nexora nexora > nexora-backup.sql`

**Important:** VM reclamation and free-tier availability are not guaranteed. No production release until functional tests, backups and security review pass. A1 uses ARM64; dependencies must be ARM-compatible. If your GitHub repository is private, use authenticated git access rather than embedding tokens in commands.
