# dotfiles/run.ps1
# Dotfiles 설정 및 실행 스크립트

# Dotfiles 디렉터리 경로 설정
$DotfilesDir = "$HOME\.dotfiles"

# 1. Dotfiles 디렉터리 확인
if (-Not (Test-Path $DotfilesDir)) {
    Write-Host "Dotfiles 디렉터리가 존재하지 않습니다: $DotfilesDir" -ForegroundColor Red
    exit 1
}

# 2. 심볼릭 링크 생성 (예: .gitconfig)
Write-Host "심볼릭 링크를 생성합니다..."
$Links = @{
    "$DotfilesDir\gitconfig" = "$HOME\.gitconfig"
    "$DotfilesDir\vimrc" = "$HOME\.vimrc"
}

foreach ($src in $Links.Keys) {
    $dst = $Links[$src]
    if (Test-Path $dst) {
        Write-Host "기존 파일/링크가 존재합니다: $dst. 건너뜁니다." -ForegroundColor Yellow
    } else {
        New-Item -ItemType SymbolicLink -Path $dst -Target $src | Out-Null
        Write-Host "심볼릭 링크 생성: $src -> $dst" -ForegroundColor Green
    }
}

# 3. winget 사용 가능 여부 확인
Write-Host "winget 사용 가능 여부를 확인합니다..."
if (-Not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "winget이 설치되어 있지 않습니다. Windows 10 1809 이상 또는 Windows 11이 필요합니다." -ForegroundColor Red
    exit 1
}

# 4. 패키지 설치 확인 및 실행 (winget)
Write-Host "필요한 패키지가 설치되어 있는지 확인합니다..."
$Packages = @{
    "Git.Git" = "Git"
    "7zip.7zip" = "7-Zip"
}

foreach ($pkgId in $Packages.Keys) {
    $pkgName = $Packages[$pkgId]
    $installed = winget list --id $pkgId -e 2>$null
    if ($LASTEXITCODE -ne 0 -or -Not ($installed | Select-String $pkgId)) {
        Write-Host "패키지가 설치되지 않았습니다: $pkgName. 설치를 진행합니다..."
        winget install --id $pkgId -e --accept-package-agreements --accept-source-agreements
    } else {
        Write-Host "패키지가 이미 설치되어 있습니다: $pkgName" -ForegroundColor Green
    }
}

# 5. 사용자 지정 스크립트 실행
Write-Host "사용자 지정 스크립트를 실행합니다..."
if (Test-Path "$DotfilesDir\custom.ps1") {
    . "$DotfilesDir\custom.ps1"
} else {
    Write-Host "사용자 지정 스크립트가 없습니다: $DotfilesDir\custom.ps1" -ForegroundColor Yellow
}

Write-Host "Dotfiles 설정 완료!" -ForegroundColor Cyan
