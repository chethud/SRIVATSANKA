# GitHub Actions → AWS EC2 deploy

Pushing to `main` runs **Deploy to AWS EC2** (`.github/workflows/deploy-aws.yml`).

## What it does

1. Verifies AWS IAM credentials (`sts get-caller-identity`)
2. Builds `website/` production bundle
3. Backs up live `kannans.db`, `.env`, `uploads`, and current `dist` on EC2
4. Overlays new frontend + backend code
5. Restarts `kannans-backend` and hits `/api/health`

**Never deletes** live database, `.env`, or uploads.

## Required GitHub secrets

Repo → **Settings → Secrets and variables → Actions**:

| Secret | Purpose |
|--------|---------|
| `AWS_ACCESS_KEY_ID` | IAM access key for GitHub |
| `AWS_SECRET_ACCESS_KEY` | IAM secret key |
| `AWS_REGION` | e.g. `ap-south-1` |
| `EC2_HOST` | e.g. `13.232.230.198` |
| `EC2_USER` | e.g. `ubuntu` |
| `EC2_SSH_PRIVATE_KEY` | Full PEM / OpenSSH private key for the EC2 instance |

## Manual run

Actions → **Deploy to AWS EC2** → **Run workflow**.

## CI only (PRs)

`.github/workflows/ci.yml` builds the website and does a light backend import check on pull requests.
