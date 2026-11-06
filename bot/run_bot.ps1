$ErrorActionPreference = 'Stop'
$BotDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $BotDir

if (-not (Test-Path "$BotDir\.env")) {
  Write-Host "لم يوجد ملف .env. انسخ .env.example إلى .env وضع المفاتيح داخله." -ForegroundColor Red
  exit 1
}

Get-Content "$BotDir\.env" | ForEach-Object {
  $line = $_.Trim()
  if ($line -and -not $line.StartsWith('#') -and $line.Contains('=')) {
    $parts = $line.Split('=', 2)
    [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), 'Process')
  }
}

$env:PYTHONPATH = $BotDir
while ($true) {
  Write-Host "$(Get-Date -Format s) تشغيل بوت سبيل الرشاد..." -ForegroundColor Green
  python "$BotDir\telegram_approval_bot.py"
  $code = $LASTEXITCODE
  Write-Host "توقف البوت برمز $code. إعادة التشغيل بعد 5 ثوانٍ..." -ForegroundColor Yellow
  Start-Sleep -Seconds 5
}
