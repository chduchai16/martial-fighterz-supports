Add-Type -AssemblyName System.Drawing

$srcPath = 'd:\python\martial-fighterz-supports\sample_images\sixth_step.png'
$outPath = 'd:\python\martial-fighterz-supports\images\out_of_items_text.png'

$src = [System.Drawing.Bitmap]::FromFile($srcPath)

# Vị trí chữ 'Không đủ vật phẩm trong kho đồ' trên sixth_step.png (567x1006):
# x: 130, y: 805, w: 280, h: 40
$rect = New-Object System.Drawing.Rectangle(130, 805, 280, 40)
$target = New-Object System.Drawing.Bitmap(280, 40)
$g = [System.Drawing.Graphics]::FromImage($target)
$dest = New-Object System.Drawing.Rectangle(0, 0, 280, 40)
$g.DrawImage($src, $dest, $rect, [System.Drawing.GraphicsUnit]::Pixel)
$g.Dispose()

$target.Save($outPath, [System.Drawing.Imaging.ImageFormat]::Png)
$target.Dispose()
$src.Dispose()

Write-Output "Successfully cropped out_of_items_text: $outPath"
