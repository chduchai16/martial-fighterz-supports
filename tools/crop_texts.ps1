Add-Type -AssemblyName System.Drawing

# 1. Crop from seventh_step.png: text "Warrior Gem"
$src = "d:\python\martial-fighterz-supports\sample_images\seventh_step.png"
$bmp = [System.Drawing.Bitmap]::FromFile($src)
$w = $bmp.Width
$h = $bmp.Height
Write-Host "seventh_step.png size: $w x $h"

# In seventh_step.png:
# Text: "1 lượt trao đổi Warrior Gem đã được kích hoạt, thật là may mắn!"
# Crop "Warrior Gem" or the text block: roughly y: 780..840 (out of 1009/1014), x: 150..450
# Let's crop "Warrior Gem" specifically:
# y ratio roughly 0.78 to 0.84, x ratio roughly 0.30 to 0.70
$wgRect = New-Object System.Drawing.Rectangle([int]($w * 0.28), [int]($h * 0.785), [int]($w * 0.45), [int]($h * 0.045))
$wgBmp = $bmp.Clone($wgRect, $bmp.PixelFormat)
$wgBmp.Save("d:\python\martial-fighterz-supports\images\warrior_gem_text.png", [System.Drawing.Imaging.ImageFormat]::Png)
$wgBmp.Dispose()
$bmp.Dispose()

# 2. Re-crop "Không còn lượt đổi nào." from media_1790478162591.png with precise boundaries
$src2 = "C:\Users\chudu\.gemini\antigravity-ide\brain\871f4870-1f15-44af-bab6-2e2b4f83574c\.user_uploaded\media_1790478162591.png"
$bmp2 = [System.Drawing.Bitmap]::FromFile($src2)
$w2 = $bmp2.Width
$h2 = $bmp2.Height
Write-Host "media_1790478162591.png size: $w2 x $h2"

# In media_1790478162591.png: Text is centered in scroll:
# Roughly x: 26% to 74%, y: 61% to 67%
$ntRect = New-Object System.Drawing.Rectangle([int]($w2 * 0.26), [int]($h2 * 0.605), [int]($w2 * 0.48), [int]($h2 * 0.065))
$ntBmp = $bmp2.Clone($ntRect, $bmp2.PixelFormat)
$ntBmp.Save("d:\python\martial-fighterz-supports\images\no_turns_text.png", [System.Drawing.Imaging.ImageFormat]::Png)
$ntBmp.Dispose()
$bmp2.Dispose()

Write-Host "All text templates cropped successfully."
