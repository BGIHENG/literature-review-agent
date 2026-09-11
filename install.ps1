# 文献综述 AI Agent Pipeline — 安装脚本 (Windows PowerShell)
$ErrorActionPreference = "Stop"

$SkillDir = Join-Path $env:USERPROFILE ".workbuddy\skills"
$SrcDir   = Join-Path $PSScriptRoot "skills"

Write-Host "================================================"
Write-Host " 文献综述 AI Agent Pipeline — 安装"
Write-Host "================================================"
Write-Host "源目录  : $SrcDir"
Write-Host "目标目录: $SkillDir"
Write-Host ""

if (-not (Test-Path $SrcDir)) {
    Write-Host "[ERROR] 找不到 skills 目录: $SrcDir" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $SkillDir)) {
    New-Item -ItemType Directory -Path $SkillDir -Force | Out-Null
}

$count = 0
Get-ChildItem -Path $SrcDir -Directory -Filter "lr-*" | ForEach-Object {
    $name = $_.Name
    $dest = Join-Path $SkillDir $name

    if (Test-Path $dest) {
        Write-Host "  [更新] $name"
    } else {
        Write-Host "  [新增] $name"
    }

    if (-not (Test-Path $dest)) {
        New-Item -ItemType Directory -Path $dest -Force | Out-Null
    }
    Copy-Item -Path (Join-Path $_.FullName "*") -Destination $dest -Recurse -Force
    $count++
}

Write-Host ""
Write-Host "已安装 $count 个 Skill 到 $SkillDir"
Write-Host ""

# 安装 Python 依赖
$pip = Get-Command pip -ErrorAction SilentlyContinue
if (-not $pip) { $pip = Get-Command pip3 -ErrorAction SilentlyContinue }

if (-not $pip) {
    Write-Host "[WARN] 未找到 pip，跳过依赖安装。请手动执行:" -ForegroundColor Yellow
    Write-Host "       pip install -r requirements.txt"
    Write-Host ""
    Write-Host "安装完成。重启 Agent 后即可使用。"
    exit 0
}

$reply = Read-Host "是否安装 Python 依赖？[y/N]"
if ($reply -match "^[yY]") {
    & $pip.Source install -r (Join-Path $PSScriptRoot "requirements.txt")
} else {
    Write-Host "已跳过。稍后可手动执行: pip install -r requirements.txt"
}

Write-Host ""
Write-Host "安装完成。重启 Agent 后即可使用。" -ForegroundColor Green
Write-Host "试试说：开始写综述：<你的选题>"
