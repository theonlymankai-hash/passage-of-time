# Render a ?shot= timeline headlessly on the GPU and wait for it to finish.
#   powershell -File render.ps1 -Shot reddit-v2 [-Out tag] [-Frames "0,200,400"]
# Needs shots/render_server.py running on :3012. Uses its own throwaway Edge
# profile, so it never touches the user's browser. Headless because a hidden
# browser pane pauses requestAnimationFrame and the splat loader stalls.
param([string]$Shot, [string]$Out = $Shot, [string]$Frames = "", [int]$From = 0, [int]$TimeoutMin = 60)
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$prof = Join-Path $env:TEMP "tree-render-edge-profile"
New-Item -ItemType Directory -Force $prof | Out-Null
$url = "http://localhost:3012/index.html?shot=$Shot&out=$Out"
if ($Frames) { $url += "&frames=$Frames" }
if ($From) { $url += "&from=$From" }
Remove-Item -Force (Join-Path $root "renders\$Out\ERROR.txt") -ErrorAction SilentlyContinue
$done = Join-Path $root "renders\$Out\DONE"
Remove-Item -Force $done -ErrorAction SilentlyContinue
$p = Start-Process -PassThru -FilePath "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" -ArgumentList @(
  "--headless=new","--enable-gpu","--ignore-gpu-blocklist","--use-angle=d3d11",
  "--window-size=1080,1350","--disable-background-timer-throttling",
  "--disable-renderer-backgrounding","--disable-backgrounding-occluded-windows",
  "--no-first-run","--user-data-dir=$prof",$url)
$deadline = (Get-Date).AddMinutes($TimeoutMin)
while (-not (Test-Path $done) -and (Get-Date) -lt $deadline) { Start-Sleep 3 }
Get-CimInstance Win32_Process -Filter "Name='msedge.exe'" |
  Where-Object { $_.CommandLine -like "*tree-render-edge-profile*" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
if (Test-Path $done) { "DONE $Out" } else { "TIMEOUT $Out"; exit 1 }
