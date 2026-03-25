# EC2 Deployment

This app is prepared for a single-host Ubuntu 24.04 deployment using:

- Gunicorn
- Nginx
- systemd
- PostgreSQL on the same EC2 host
- Let's Encrypt / Certbot for TLS

## Host layout

- App repo: `/srv/trading-pro/app`
- Venv: `/srv/trading-pro/venv`
- Env file: `/etc/trading-pro/trading-pro.env`
- Gunicorn socket: `/run/trading-pro/gunicorn.sock`
- Static files: `/srv/trading-pro/static`
- Backups: `/srv/trading-pro/backups/`

## Provision the EC2 host

1. Install the AWS CLI locally or use AWS CloudShell.
2. Copy the stack template env file:

   ```bash
   cp deploy/ec2/aws-stack.env.example deploy/ec2/aws-stack.env
   ```

3. Fill in:
   - `AWS_REGION`
   - `VPC_ID`
   - `SUBNET_ID`
   - `KEY_PAIR_NAME`
   - `ADMIN_CIDR`
   - optional stack naming overrides
4. Launch the EC2 stack:

   ```bash
   bash scripts/ec2/aws_launch_stack.sh
   ```

That creates:

- one Ubuntu 24.04 EC2 instance
- one Elastic IP
- one security group with `22/80/443` open and no public `5432`
- one instance profile with `AmazonSSMManagedInstanceCore`

## First-time bootstrap

1. Point your DNS `A` record to the Elastic IP from the stack output.
2. SSH into the instance with your EC2 key pair.
3. Copy the deploy-key helper to the host:

   ```bash
   scp scripts/ec2/configure_github_deploy_key.sh ubuntu@EC2_PUBLIC_IP:/tmp/configure_github_deploy_key.sh
   ```

4. Install the GitHub deploy key on the instance:

   ```bash
   sudo GITHUB_REPO_SSH_URL=git@github.com:owner/repo.git \
     bash /tmp/configure_github_deploy_key.sh /path/to/github-deploy-key
   ```

   Optionally set `GITHUB_REPO_SSH_URL=git@github.com:owner/repo.git` before running the script to clone the repo automatically into `/srv/trading-pro/app`.

5. If the repo was not cloned automatically, clone it manually into `/srv/trading-pro/app`.
6. Copy the env template:

   ```bash
   sudo mkdir -p /etc/trading-pro
   sudo cp /srv/trading-pro/app/deploy/ec2/trading-pro.env.example /etc/trading-pro/trading-pro.env
   sudo nano /etc/trading-pro/trading-pro.env
   ```

7. Run the bootstrap script:

   ```bash
   cd /srv/trading-pro/app
   sudo bash scripts/ec2/bootstrap_ec2.sh
   ```

8. Run the first deploy:

   ```bash
   sudo bash scripts/ec2/deploy_ec2.sh
   ```

9. Issue TLS certificates after Nginx is serving your domain:

   ```bash
   sudo certbot --nginx -d example.com -d www.example.com
   ```

   Certbot will update the Nginx site to terminate HTTPS and redirect HTTP to HTTPS.

10. Verify:

   ```bash
   curl -I https://example.com/health/
   ```

## Repeat deploys

```bash
cd /srv/trading-pro/app
sudo bash scripts/ec2/deploy_ec2.sh
```

That flow:

- pulls the latest code
- updates Python packages in the venv
- runs Django migrations
- runs `collectstatic --noinput`
- restarts Gunicorn
- verifies `/health/`

## PostgreSQL backup

Run the backup script manually:

```bash
sudo bash /srv/trading-pro/app/scripts/ec2/backup_postgres.sh
```

Suggested daily cron entry:

```cron
0 2 * * * root /srv/trading-pro/app/scripts/ec2/backup_postgres.sh >> /var/log/trading-pro-backup.log 2>&1
```

Backups are written to `/srv/trading-pro/backups/` and old files older than 14 days are pruned automatically.

## Operational checks

- Gunicorn logs: `sudo journalctl -u trading-pro -f`
- Nginx config test: `sudo nginx -t`
- Nginx reload: `sudo systemctl reload nginx`
- App health through Gunicorn socket:

  ```bash
  curl --unix-socket /run/trading-pro/gunicorn.sock \
    -H 'X-Forwarded-Proto: https' \
    http://localhost/health/
  ```
