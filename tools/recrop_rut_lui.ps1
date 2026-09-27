Add-Type -AssemblyName System.Drawing

$srcPath = 'd:\python\martial-fighterz-supports\sample_images\fifth_step.png'
$outPath = 'd:\python\martial-fighterz-supports\images\rut_lui_button.png'

$src = [System.Drawing.Bitmap]::FromFile($srcPath)

# Vị trí nút Rút lui chuẩn: x: 215, y: 614, w: 140, h: 46
$rect = New-Object System.Drawing.Rectangle(215, 614, 140, 46)
$target = New-Object System.Drawing.Bitmap(140, 46)
$g = [System.Drawing.Graphics]::FromImage($target)
$dest = New-Object System.Drawing.Rectangle(0, 0, 140, 46)
$g.DrawImage($src, $dest, $rect, [System.Drawing.GraphicsUnit]::Pixel)
$g.Dispose()

$target.Save($outPath, [System.Drawing.Imaging.ImageFormat]::Png)
$target.Dispose()
$src.Dispose()

Write-Output "Perfect cropped: $outPath"
