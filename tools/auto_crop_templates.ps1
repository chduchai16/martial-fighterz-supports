Add-Type -AssemblyName System.Drawing

$srcPath = 'd:\python\martial-fighterz-supports\sample_images\first_step.png'
$imgDir = 'd:\python\martial-fighterz-supports\images'

$src = [System.Drawing.Bitmap]::FromFile($srcPath)

function CropAndSave($x, $y, $w, $h, $name) {
    $rect = New-Object System.Drawing.Rectangle([int]$x, [int]$y, [int]$w, [int]$h)
    $target = New-Object System.Drawing.Bitmap([int]$w, [int]$h)
    $g = [System.Drawing.Graphics]::FromImage($target)
    $destRect = New-Object System.Drawing.Rectangle(0, 0, [int]$w, [int]$h)
    $g.DrawImage($src, $destRect, $rect, [System.Drawing.GraphicsUnit]::Pixel)
    $g.Dispose()
    
    $outPath = Join-Path $imgDir $name
    $target.Save($outPath, [System.Drawing.Imaging.ImageFormat]::Png)
    $target.Dispose()
    Write-Output "Extracted template: $name -> $outPath"
}

# Crop Odd Button
CropAndSave 452 288 84 84 "odd_button.png"

# Crop Even Button
CropAndSave 452 384 84 84 "even_button.png"

# Crop VIP7 Dice Tab
CropAndSave 415 198 60 62 "vip7_tab.png"

# Crop VIP9 Dice Tab
CropAndSave 488 198 60 62 "vip9_tab.png"

# Crop Refresh / Reset Button
CropAndSave 8 215 130 40 "reset_button.png"

$src.Dispose()
Write-Output "All templates extracted successfully."
