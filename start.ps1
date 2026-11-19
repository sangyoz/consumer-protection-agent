param(
  [ValidateSet('start', 'stop', 'status')]
  [string]$Action = 'start',
  [ValidateSet('sqlite', 'mysql')]
  [string]$Database = 'mysql',
  [switch]$OpenBrowser
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RunRoot = Join-Path $ProjectRoot '.run'
$LogRoot = Join-Path $RunRoot 'logs'
$StatePath = Join-Path $RunRoot 'services.json'
$ApiPort = 8000
$WebPort = 5173

function Read-State {
  if (Test-Path -LiteralPath $StatePath) {
    try { return Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json } catch { return $null }
  }
  return $null
}

function Test-Port([int]$Port) {
  $client = [System.Net.Sockets.TcpClient]::new()
  try {
    $result = $client.BeginConnect('127.0.0.1', $Port, $null, $null)
    $client.EndConnect($result)
    return $client.Connected
  } catch { return $false } finally { $client.Dispose() }
}

function Stop-ManagedProcess($Entry) {
  if (-not $Entry) { return }
  $owners = @()
  foreach ($line in (netstat.exe -ano -p tcp)) {
    if ($line -match "^\s*TCP\s+\S+:$([int]$Entry.port)\s+\S+\s+LISTENING\s+(\d+)\s*$") {
      $owners += [int]$Matches[1]
    }
  }
  $targets = @($owners + @([int]$Entry.pid) | Sort-Object -Unique)
  foreach ($processId in $targets) {
    try { Stop-Process -Id $processId -Force -ErrorAction Stop } catch { }
  }
  if ($targets.Count) {
    Write-Host ('已停止 {0}（端口 {1}）' -f $Entry.name, $Entry.port)
  } else {
    Write-Host "$($Entry.name) 已停止"
  }
}

if ($Action -eq 'status') {
  $state = Read-State
  if ($state) {
    Write-Host ("数据库模式：{0}" -f $state.database)
    foreach ($entry in @($state.frontend, $state.backend)) {
      $running = Test-Port ([int]$entry.port)
      $label = if ($running) { '运行中' } else { '未运行' }
      Write-Host ("{0}: {1} (127.0.0.1:{2})" -f $entry.name, $label, $entry.port)
    }
  } else { Write-Host '当前没有一键启动的服务。' }
  exit 0
}

if ($Action -eq 'stop') {
  $state = Read-State
  if ($state) {
    Stop-ManagedProcess $state.frontend
    Stop-ManagedProcess $state.backend
    Remove-Item -LiteralPath $StatePath -Force -ErrorAction SilentlyContinue
  } else { Write-Host '没有一键启动记录。' }
  Write-Host 'MySQL 数据库保持运行，数据不会删除。项目本地数据库位于 .run/mysql/。'
  exit 0
}

New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null
$backendEnv = Join-Path $ProjectRoot 'backend\.env'
if (-not (Test-Path -LiteralPath $backendEnv)) {
  Copy-Item -LiteralPath (Join-Path $ProjectRoot 'backend\.env.example') -Destination $backendEnv
}

$previousState = Read-State
if ($previousState) {
  Stop-ManagedProcess $previousState.frontend
  Stop-ManagedProcess $previousState.backend
  Remove-Item -LiteralPath $StatePath -Force -ErrorAction SilentlyContinue
  Start-Sleep -Milliseconds 500
}

$occupied = @()
if (Test-Port $ApiPort) { $occupied += "API $ApiPort" }
if (Test-Port $WebPort) { $occupied += "前端 $WebPort" }
if ($occupied.Count) { throw "需要的端口已被占用：$($occupied -join '、')。关闭占用程序后再运行。" }

$nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
$pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
if (-not $nodeCommand) { throw '没有找到 Node.js。请安装 Node.js 20.19+ 后重试。' }
if (-not $pythonCommand) { throw '没有找到 Python。请安装 Python 3.10+ 并加入 PATH 后重试。' }

$nodeVersion = [version]((& $nodeCommand.Source --version | Out-String).Trim().TrimStart('v'))
if ($nodeVersion.Major -lt 20 -or ($nodeVersion.Major -eq 20 -and $nodeVersion.Minor -lt 19)) { throw '前端需要 Node.js 20.19+。' }

$venvPython = Join-Path $ProjectRoot 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
  Write-Host '首次启动：创建后端虚拟环境…' -ForegroundColor Cyan
  & $pythonCommand.Source -m venv (Join-Path $ProjectRoot 'backend\.venv')
  if ($LASTEXITCODE -ne 0) { throw '创建 Python 虚拟环境失败。' }
}

& $venvPython -c 'import fastapi, uvicorn, sqlalchemy, multipart, dotenv, langgraph, langchain_openai, pymysql, cryptography' 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Host '首次启动或后端依赖有更新：安装后端依赖…' -ForegroundColor Cyan
  & $venvPython -m pip install -r (Join-Path $ProjectRoot 'backend\requirements.txt')
  if ($LASTEXITCODE -ne 0) { throw '安装后端依赖失败，请检查网络并重试。' }
}

$viteEntry = Join-Path $ProjectRoot 'frontend\node_modules\vite\bin\vite.js'
if (-not (Test-Path -LiteralPath $viteEntry)) {
  Write-Host '首次启动：安装前端依赖…' -ForegroundColor Cyan
  Push-Location $ProjectRoot
  try { & npm.cmd install --prefix frontend } finally { Pop-Location }
  if ($LASTEXITCODE -ne 0) { throw '安装前端依赖失败，请检查网络并重试。' }
}

if ($Database -eq 'mysql') {
  Write-Host '准备 MySQL 并核对案件数据…' -ForegroundColor Cyan
  & $venvPython (Join-Path $ProjectRoot 'backend\tools\setup_mysql.py')
  if ($LASTEXITCODE -ne 0) { throw 'MySQL 配置失败，请根据上面的提示检查后重试。' }
  $env:DATABASE_URL = (((Get-Content -LiteralPath $backendEnv | Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -First 1) -replace '^DATABASE_URL=', '').Trim()).Trim([char]39, [char]34)
} else {
  $databaseFile = (Join-Path $ProjectRoot 'backend\youli.db').Replace('\', '/')
  $env:DATABASE_URL = "sqlite:///$databaseFile"
}

$env:CORS_ORIGINS = 'http://127.0.0.1:5173,http://localhost:5173'
$env:API_PROXY_TARGET = "http://127.0.0.1:$ApiPort"
$env:VITE_API_BASE_URL = '/api'
$env:VITE_DATA_MODE = 'api'

$backendOut = Join-Path $LogRoot 'backend.out.log'
$backendErr = Join-Path $LogRoot 'backend.err.log'
$frontendOut = Join-Path $LogRoot 'frontend.out.log'
$frontendErr = Join-Path $LogRoot 'frontend.err.log'
$backendProcess = Start-Process -FilePath $venvPython -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', "$ApiPort") -WorkingDirectory (Join-Path $ProjectRoot 'backend') -WindowStyle Hidden -RedirectStandardOutput $backendOut -RedirectStandardError $backendErr -PassThru
$frontendProcess = Start-Process -FilePath $nodeCommand.Source -ArgumentList @($viteEntry, '--host', '127.0.0.1', '--port', "$WebPort", '--strictPort') -WorkingDirectory (Join-Path $ProjectRoot 'frontend') -WindowStyle Hidden -RedirectStandardOutput $frontendOut -RedirectStandardError $frontendErr -PassThru

$state = [ordered]@{
  database = $Database
  backend = @{ name = '后端'; pid = $backendProcess.Id; port = $ApiPort }
  frontend = @{ name = '前端'; pid = $frontendProcess.Id; port = $WebPort }
}
$state | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $StatePath -Encoding utf8

$ready = $false
for ($attempt = 0; $attempt -lt 45; $attempt++) {
  try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:$ApiPort/api/health" -TimeoutSec 2
    if ($health.status -eq 'ok') { $ready = $true; break }
  } catch { Start-Sleep -Milliseconds 1000 }
}
$frontendReady = $false
try {
  $frontendResponse = Invoke-WebRequest -Uri "http://127.0.0.1:$WebPort" -UseBasicParsing -TimeoutSec 3
  $frontendReady = $frontendResponse.StatusCode -eq 200
} catch { }
if (-not $ready -or -not $frontendReady) {
  $apiLog = if (Test-Path $backendErr) { Get-Content $backendErr -Tail 20 } else { @() }
  $viteLog = if (Test-Path $frontendErr) { Get-Content $frontendErr -Tail 20 } else { @() }
  Write-Host '服务没有正常启动，错误日志如下：' -ForegroundColor Red
  $apiLog; $viteLog
  Stop-ManagedProcess $state.frontend
  Stop-ManagedProcess $state.backend
  throw '一键启动失败。请检查 .run/logs/ 下的日志。'
}

$agentLabel = if ($health.agentMode -eq 'deepseek') { 'DeepSeek + LangGraph' } else { '演示规则 + LangGraph' }
Write-Host "`n前端已启动：http://127.0.0.1:$WebPort" -ForegroundColor Green
Write-Host "后端接口文档：http://127.0.0.1:$ApiPort/docs"
Write-Host "数据库：$Database；Agent：$agentLabel"
Write-Host "日志目录：$LogRoot"
Write-Host '停止前后端：stop.bat；MySQL 数据库和数据文件会保持不变。'
if ($OpenBrowser) {
  try { Start-Process "http://127.0.0.1:$WebPort" -ErrorAction Stop } catch {
    Write-Warning "浏览器未能自动打开，请手动访问 http://127.0.0.1:$WebPort"
  }
}
