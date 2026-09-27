Add-Type -AssemblyName System.Drawing

$src = "C:\Users\chudu\.gemini\antigravity-ide\brain\871f4870-1f15-44af-bab6-2e2b4f83574c\.user_uploaded\media_1790478162591.png"
$bmp = [System.Drawing.Bitmap]::FromFile($src)
$w = $bmp.Width
$h = $bmp.Height
Write-Host "Source image size: $w x $h"

# 1. Crop Arale Hat/Face: Top-left area (roughly x=20..180, y=50..220 in relative coords)
# In image: Arale is roughly x: 20 to 180, y: 50 to 220
# Let's crop Arale hat ("ARALE")
$araleRect = New-Object System.Drawing.Rectangle([int]($w * 0.05), [int]($h * 0.10), [int]($w * 0.28), [int]($h * 0.25))
$araleBmp = $bmp.Clone($araleRect, $bmp.PixelFormat)
$araleBmp.Save("d:\python\martial-fighterz-supports\images\arale_header.png", [System.Drawing.Imaging.ImageFormat]::Png)
$araleBmp.Dispose()

# 2. Crop text "Không còn lượt đổi nào." (center scroll area, roughly x: 25%..75%, y: 58%..70%)
$textRect = New-Object System.Drawing.Rectangle([int]($w * 0.25), [int]($h * 0.58), [int]($w * 0.45), [int]($h * 0.10))
$textBmp = $bmp.Clone($textRect, $bmp.PixelFormat)
$textBmp.Save("d:\python\martial-fighterz-supports\images\no_turns_text.png", [System.Drawing.Imaging.ImageFormat]::Png)
$textBmp.Dispose()

# 3. Crop OK button on this scroll
$okRect = New-Object System.Drawing.Rectangle([int]($w * 0.33), [int]($h * 0.72), [int]($w * 0.22), [int]($h * 0.14))
$okBmp = $bmp.Clone($okRect, $bmp.PixelFormat)
$okBmp.Save("d:\python\martial-fighterz-supports\images\ok_button.png", [System.Drawing.Imaging.ImageFormat]::Png)
$okBmp.Dispose()

$bmp.Dispose()
Write-Host "Cropped templates successfully."
