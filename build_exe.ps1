# build_exe.ps1
# Script tự động build MartialFighterz-Bot thành file .exe
# Chạy bằng:  .\build_exe.ps1

$ErrorActionPreference = "Stop"

# Tìm Python
$PYTHON = $null
$candidates = @(
    "C:\Users\chudu\AppData\Local\Programs\Python\Python313\python.exe",
    "C:\Users\chudu\AppData\Local\Programs\Python\Python312\python.exe",
    "C:\Users\chudu\AppData\Local\Programs\Python\Python311\python.exe",
    "C:\Python313\python.exe",
    "C:\Python312\python.exe"
)
foreach ($c in $candidates) {
    if (Test-Path $c) { $PYTHON = $c; break }
}
if (-not $PYTHON) { 
    Write-Host "❌ Không tìm được python.exe! Hãy cài Python trước." -ForegroundColor Red
    exit 1
}
Write-Host "✅ Dùng Python: $PYTHON" -ForegroundColor Green

# Đảm bảo PyInstaller đã cài
Write-Host "📦 Kiểm tra / cài PyInstaller..." -ForegroundColor Cyan
& $PYTHON -m pip install pyinstaller --quiet

# Kiểm tra customtkinter
Write-Host "📦 Kiểm tra customtkinter..." -ForegroundColor Cyan
& $PYTHON -m pip install customtkinter --quiet

# Copy images sang assets/templates nếu chưa đồng bộ
Write-Host "🔄 Đồng bộ images/ -> assets/templates/ ..." -ForegroundColor Cyan
if (-not (Test-Path "assets\templates")) { New-Item -ItemType Directory "assets\templates" | Out-Null }
Copy-Item "images\*" "assets\templates\" -Force -ErrorAction SilentlyContinue

# Xoá build cũ nếu có
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist\MartialFighterz-Bot") { Remove-Item -Recurse -Force "dist\MartialFighterz-Bot" }

# Build
Write-Host "🔨 Đang build exe... (có thể mất 2-5 phút)" -ForegroundColor Yellow
& $PYTHON -m PyInstaller build_exe.spec --clean --noconfirm

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ BUILD THÀNH CÔNG!" -ForegroundColor Green
    Write-Host "📁 File exe nằm tại: dist\MartialFighterz-Bot\MartialFighterz-Bot.exe" -ForegroundColor Green
    Write-Host "💡 Copy cả thư mục dist\MartialFighterz-Bot\ để chạy trên máy khác." -ForegroundColor Cyan
} else {
    Write-Host "❌ Build thất bại! Xem log lỗi ở trên." -ForegroundColor Red
    exit 1
}
