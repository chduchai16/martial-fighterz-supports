Add-Type -AssemblyName System.Drawing

$srcPath = 'd:\python\martial-fighterz-supports\sample_images\fourth_step.png'
$outAnnotated = 'd:\python\martial-fighterz-supports\sample_images\fourth_step_annotated.png'
$imgDir = 'd:\python\martial-fighterz-supports\images'

$src = [System.Drawing.Bitmap]::FromFile($srcPath)

# 1. Cắt template Kim Cương
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
    Write-Output "Extracted: $name -> $outPath"
}

# Cắt ô icon Kim Cương full tile
CropAndSave 457 601 85 85 "kim_cuong_icon.png"

# Cắt cụm 3 viên kim cương bên trong (cho template matching độ chính xác cao)
CropAndSave 463 615 72 60 "kim_cuong_inner.png"

# 2. Vẽ Annotated Image cho VIP9
$bmp = [System.Drawing.Bitmap]::FromFile($srcPath)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias

$font = New-Object System.Drawing.Font('Arial', 7.0, [System.Drawing.FontStyle]::Bold)
$penDiamondRow = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 0, 255, 255), 3) # Cyan sáng cho dòng có Kim Cương
$penRow = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 255, 215, 0), 2)
$penRow.DashStyle = [System.Drawing.Drawing2D.DashStyle]::Dash
$penDiamond = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 0, 255, 0), 3)
$penSwipe = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 255, 50, 50), 3)
$penSwipe.DashStyle = [System.Drawing.Drawing2D.DashStyle]::Dot

$brushBg = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(235, 15, 15, 15))
$brushCyanBg = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(240, 0, 80, 100))
$brushText = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::White)
$brushCenter = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 255, 40, 40))

# Dòng 1 (CÓ KIM CƯƠNG)
$r1 = New-Object System.Drawing.Rectangle(5, 589, 557, 128)
$g.DrawRectangle($penDiamondRow, $r1)
$g.FillEllipse($brushCenter, 283 - 5, 653 - 5, 10, 10)
$lbl1 = "VIP9 - DONG 1: [PHAT HIEN KIM CUONG -> CLICK TAI DAY]"
$sz1 = $g.MeasureString($lbl1, $font)
$g.FillRectangle($brushCyanBg, 8, 592, [int]$sz1.Width + 4, [int]$sz1.Height + 2)
$g.DrawString($lbl1, $font, $brushText, [float]10, [float]593)

# Highlight ô Kim Cương trong Dòng 1
$boxDiam1 = New-Object System.Drawing.Rectangle(345, 601, 85, 85)
$boxDiam2 = New-Object System.Drawing.Rectangle(457, 601, 85, 85)
$g.DrawRectangle($penDiamond, $boxDiam1)
$g.DrawRectangle($penDiamond, $boxDiam2)

# Dòng 2
$r2 = New-Object System.Drawing.Rectangle(5, 728, 557, 128)
$g.DrawRectangle($penRow, $r2)
$g.FillEllipse($brushCenter, 283 - 5, 792 - 5, 10, 10)
$lbl2 = "VIP9 - Dong 2 (Panzy 5*)"
$sz2 = $g.MeasureString($lbl2, $font)
$g.FillRectangle($brushBg, 8, 731, [int]$sz2.Width + 4, [int]$sz2.Height + 2)
$g.DrawString($lbl2, $font, $brushText, [float]10, [float]732)

# Dòng 3 (bị che nửa dưới)
$r3 = New-Object System.Drawing.Rectangle(5, 867, 557, 128)
$g.DrawRectangle($penRow, $r3)
$g.FillEllipse($brushCenter, 283 - 5, 925 - 5, 10, 10)
$lbl3 = "VIP9 - Dong 3 (Bi che 1/2 - Neu khong thay Kim Cuong o D1/D2/D3 -> Cuon len)"
$sz3 = $g.MeasureString($lbl3, $font)
$g.FillRectangle($brushBg, 8, 870, [int]$sz3.Width + 4, [int]$sz3.Height + 2)
$g.DrawString($lbl3, $font, $brushText, [float]10, [float]871)

# Vẽ mũi tên hướng dẫn cuộn lên (Swipe Up)
$pStart = New-Object System.Drawing.Point(283, 850)
$pEnd = New-Object System.Drawing.Point(283, 620)
$penArrow = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 255, 255, 0), 4)
$penArrow.CustomEndCap = New-Object System.Drawing.Drawing2D.AdjustableArrowCap(6, 6)
$g.DrawLine($penArrow, $pStart, $pEnd)

$lblSwipe = "[HUONG DAN CUON LEN DE HIEN THI DONG 4]"
$szS = $g.MeasureString($lblSwipe, $font)
$g.FillRectangle($brushBg, 180, 700, [int]$szS.Width + 4, [int]$szS.Height + 2)
$g.DrawString($lblSwipe, $font, $brushText, [float]182, [float]701)

$g.Dispose()
$bmp.Save($outAnnotated, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
$src.Dispose()

Write-Output "SUCCESS: Annotated image created at $outAnnotated"
