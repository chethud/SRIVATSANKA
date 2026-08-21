# Backup-first AWS redeploy. Never deletes live DB, .env, or uploads.
# Usage: powershell -File whatsapp\scripts\aws-redeploy.ps1

param(
    [string]$RepoRoot = "D:\Kannans",
    [string]$KeyPath = "D:\Kannans\kannans-key-pair.pem",
    [string]$SshTarget = "ubuntu@13.232.230.198"
)

$ErrorActionPreference = "Stop"
$Remote = "/home/ubuntu/srivatsanka"
$BackupRoot = "/home/ubuntu/srivatsanka-backups"
$SshOpts = @("-i", $KeyPath, "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=20")

if (-not (Test-Path $KeyPath)) { throw "SSH key missing: $KeyPath" }
if (-not (Test-Path "$RepoRoot\website\.env.production")) {
    Write-Warning "website/.env.production not found - build may use defaults."
}

function Invoke-Remote([string]$Command) {
    $bash = ($Command -replace "`r", "").Trim()
    $bash | & ssh @SshOpts $SshTarget "bash -s"
    if ($LASTEXITCODE -ne 0) { throw "Remote command failed." }
}

Write-Host "1/5 Backup live files on EC2..."
$backup = @'
set -e
STAMP=$(date +%Y%m%d_%H%M%S)
DEST=__BACKUP_ROOT__/$STAMP
mkdir -p "$DEST/whatsapp" "$DEST/website"
cp -a __REMOTE__/whatsapp/kannans.db "$DEST/whatsapp/" 2>/dev/null || true
cp -a __REMOTE__/whatsapp/.env "$DEST/whatsapp/" 2>/dev/null || true
if [ -d __REMOTE__/whatsapp/uploads ]; then cp -a __REMOTE__/whatsapp/uploads "$DEST/whatsapp/uploads"; fi
if [ -d __REMOTE__/website/dist ]; then cp -a __REMOTE__/website/dist "$DEST/website/dist"; fi
cp -a __REMOTE__/website/.env.production "$DEST/website/" 2>/dev/null || true
echo BACKUP_OK $DEST
'@ -replace '__REMOTE__', $Remote -replace '__BACKUP_ROOT__', $BackupRoot
Invoke-Remote $backup

Write-Host "2/5 Build frontend locally..."
Push-Location "$RepoRoot\website"
if (Test-Path package-lock.json) { npm ci } else { npm install }
npm run build
Pop-Location

$DistTar = "$RepoRoot\website-dist-deploy.tar"
$BackendTar = "$RepoRoot\backend-deploy.tar"
foreach ($t in @($DistTar, $BackendTar)) {
    if (Test-Path $t) { Remove-Item $t -Force }
}

tar -cf $DistTar -C "$RepoRoot\website\dist" .
Get-ChildItem -Path "$RepoRoot\whatsapp\app" -Recurse -Force | ForEach-Object { $_.Attributes = $_.Attributes -band (-bnot [IO.FileAttributes]::ReadOnly) }
tar --format=ustar --exclude=__pycache__ --exclude=*.pyc -cf $BackendTar -C "$RepoRoot\whatsapp\app" .

Write-Host "3/5 Upload frontend dist and full backend app tree..."
& scp @SshOpts $DistTar "${SshTarget}:/tmp/website-dist-deploy.tar"
& scp @SshOpts $BackendTar "${SshTarget}:/tmp/backend-deploy.tar"
if ($LASTEXITCODE -ne 0) { throw "scp failed" }

Write-Host "4/5 Overlay on EC2 and restart backend..."
$deploy = @'
set -e
chmod -R u+w __REMOTE__/website/dist 2>/dev/null || true
rm -rf __REMOTE__/website/dist/*
mkdir -p __REMOTE__/website/dist
tar -xf /tmp/website-dist-deploy.tar -C __REMOTE__/website/dist
rm -f /tmp/website-dist-deploy.tar
sudo rm -rf /tmp/backend-overlay /tmp/backend-overlay-* /tmp/bo-new /tmp/bo-* 2>/dev/null || true
OVERLAY=/tmp/backend-overlay-$$
mkdir -p "$OVERLAY"
umask 022
tar --no-same-permissions -xf /tmp/backend-deploy.tar -C "$OVERLAY"
chmod -R u+w "$OVERLAY" __REMOTE__/whatsapp/app 2>/dev/null || true
cp -rf "$OVERLAY"/. __REMOTE__/whatsapp/app/
rm -rf "$OVERLAY"
rm -f /tmp/backend-deploy.tar
if [ -f __REMOTE__/whatsapp/.env ]; then
  if grep -q '^ENVIRONMENT=' __REMOTE__/whatsapp/.env; then
    sed -i 's/^ENVIRONMENT=.*/ENVIRONMENT=production/' __REMOTE__/whatsapp/.env
  else
    echo 'ENVIRONMENT=production' >> __REMOTE__/whatsapp/.env
  fi
fi
sudo systemctl restart kannans-backend
sleep 3
sudo systemctl is-active kannans-backend
curl -sf --max-time 10 http://127.0.0.1:8000/api/health
echo
test -f __REMOTE__/whatsapp/kannans.db && echo DB_STILL_THERE
test -d __REMOTE__/whatsapp/uploads && echo UPLOADS_STILL_THERE || echo UPLOADS_DIR_OPTIONAL
'@ -replace '__REMOTE__', $Remote
Invoke-Remote $deploy

Remove-Item $DistTar, $BackendTar -Force -ErrorAction SilentlyContinue
Write-Host "5/5 Done. Live DB, .env, and uploads were backed up under $BackupRoot."
