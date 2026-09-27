Add-Type -AssemblyName System.Drawing

$imgDir = 'd:\python\martial-fighterz-supports\images'
$sampleDir = 'd:\python\martial-fighterz-supports\sample_images'

# Copy fifth and sixth to sample_images
Copy-Item (Join-Path $imgDir 'fifth_step.png') (Join-Path $sampleDir 'fifth_step.png') -Force
Copy-Item (Join-Path $imgDir 'sixth_step.png') (Join-Path $sampleDir 'sixth_step.png') -Force

# 1. Cắt nút Rút lui từ fifth_step.png
$src5 = [System.Drawing.Bitmap]::FromFile((Join-Path $sampleDir 'fifth_step.png'))
# Vị trí nút Rút lui trên fifth_step.png: x: 220, y: 630, w: 135, h: 42
$rect5 = New-Object System.Drawing.Rectangle(220, 630, 135, 42)
$target5 = New-Object System.Drawing.Bitmap(135, 42)
$g5 = [System.Drawing.Graphics]::FromImage($target5)
$dest5 = New-Object System.Drawing.Rectangle(0, 0, 135, 42)
$g5.DrawImage($src5, $dest5, $rect5, [System.Drawing.GraphicsUnit]::Pixel)
$g5.Dispose()

$rutLuiPath = Join-Path $imgDir 'rut_lui_button.png'
$target5.Save($rutLuiPath, [System.Drawing.Imaging.ImageFormat]::Png)
$target5.Dispose()
$src5.Dispose()
Write-Output "Extracted: rut_lui_button.png -> $rutLuiPath"

# 2. Cắt nút OK từ sixth_step.png
$src6 = [System.Drawing.Bitmap]::FromFile((Join-Path $sampleDir 'sixth_step.png'))
# Vị trí nút OK trên sixth_step.png: x: 215, y: 865, w: 105, h: 45
$rect6 = New-Object System.Drawing.Rectangle(215, 865, 105, 45)
$target6 = New-Object System.Drawing.Bitmap(105, 45)
$g6 = [System.Drawing.Graphics]::FromImage($target6)
$dest6 = New-Object System.Drawing.Rectangle(0, 0, 105, 45)
$g6.DrawImage($src6, $dest6, $rect6, [System.Drawing.GraphicsUnit]::Pixel)
$g6.Dispose()

$okPath = Join-Path $imgDir 'ok_button.png'
$target6.Save($okPath, [System.Drawing.Imaging.ImageFormat]::Png)
$target6.Dispose()
$src6.Dispose()
Write-Output "Extracted: ok_button.png -> $okPath"
