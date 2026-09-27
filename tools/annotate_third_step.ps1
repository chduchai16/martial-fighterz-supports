Add-Type -AssemblyName System.Drawing

$srcPath = 'd:\python\martial-fighterz-supports\sample_images\third_step.png'
$outPath = 'd:\python\martial-fighterz-supports\sample_images\third_step_annotated.png'

$bmp = [System.Drawing.Bitmap]::FromFile($srcPath)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias

$font = New-Object System.Drawing.Font('Arial', 7.0, [System.Drawing.FontStyle]::Bold)
$penRow = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 255, 215, 0), 3)
$penRow.DashStyle = [System.Drawing.Drawing2D.DashStyle]::Dash
$penCyan = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 0, 230, 255), 2)
$penMagenta = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 255, 0, 255), 2)
$penYellow = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 255, 220, 0), 2)
$penRed = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 255, 60, 60), 2)
$brushBg = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(235, 15, 15, 15))
$brushText = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::White)
$brushCenter = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 255, 40, 40))

# Toạ độ trên third_step.png (có offset +49px do thanh tiêu đề cửa sổ)
$offsetY = 49

# 1. VIP7 Tab (Tab 3)
$tab3 = New-Object System.Drawing.Rectangle(414, (196 + $offsetY), 65, 70)
$g.DrawRectangle($penYellow, $tab3)
$g.FillEllipse($brushCenter, 446 - 4, (231 + $offsetY) - 4, 8, 8)

# 2. Buttons Odd / Even
$btnOdd = New-Object System.Drawing.Rectangle(452, (286 + $offsetY), 92, 92)
$g.DrawRectangle($penCyan, $btnOdd)
$g.FillEllipse($brushCenter, 498 - 4, (332 + $offsetY) - 4, 8, 8)

$btnEven = New-Object System.Drawing.Rectangle(452, (382 + $offsetY), 92, 92)
$g.DrawRectangle($penYellow, $btnEven)
$g.FillEllipse($brushCenter, 498 - 4, (428 + $offsetY) - 4, 8, 8)

# 3. Ba Dòng VIP7 (Row 1, Row 2, Row 3)
$rows = @(
    @{ name = "VIP7 - Dong 1"; y = 593; input = "Linh Hon Saiyan (300)"; reward = "Phuc Tung D" },
    @{ name = "VIP7 - Dong 2"; y = 732; input = "Linh Hon Saiyan (300)"; reward = "Nhiet Huyet D" },
    @{ name = "VIP7 - Dong 3 (Bi che mot nua van click duoc)"; y = 872; input = "Linh Hon Saiyan"; reward = "Nhiet Huyet D" }
)

foreach ($r in $rows) {
    $ry = $r.y + $offsetY
    $rect = New-Object System.Drawing.Rectangle(6, $ry, 558, 128)
    $g.DrawRectangle($penRow, $rect)
    
    # Center Point
    $cx = 285
    $cy = $ry + 55  # Đặt tâm bấm cao hơn 1 chút ở dòng 3 để không bị vướng thanh điều hướng dưới
    $g.FillEllipse($brushCenter, $cx - 5, $cy - 5, 10, 10)
    
    # Label Row
    $lbl = $r.name
    $sz = $g.MeasureString($lbl, $font)
    $g.FillRectangle($brushBg, 10, $ry + 2, [int]$sz.Width + 4, [int]$sz.Height + 2)
    $g.DrawString($lbl, $font, $brushText, [float]12, [float]($ry + 3))
    
    # Input Box
    $inRect = New-Object System.Drawing.Rectangle(45, ($ry + 12), 85, 85)
    $g.DrawRectangle($penCyan, $inRect)
    
    # Reward Box
    $rewRect = New-Object System.Drawing.Rectangle(458, ($ry + 12), 85, 85)
    $g.DrawRectangle($penMagenta, $rewRect)
}

$g.Dispose()
$bmp.Save($outPath, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output "SUCCESS: $outPath"
