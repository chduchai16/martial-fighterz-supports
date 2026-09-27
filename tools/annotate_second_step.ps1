Add-Type -AssemblyName System.Drawing

$json = Get-Content 'd:\python\martial-fighterz-supports\coordinates.json' -Raw | ConvertFrom-Json
$srcPath = 'd:\python\martial-fighterz-supports\sample_images\second_step.png'
$outPath = 'd:\python\martial-fighterz-supports\sample_images\second_step_annotated.png'

$bmp = [System.Drawing.Bitmap]::FromFile($srcPath)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias

$font = New-Object System.Drawing.Font('Arial', 6.8, [System.Drawing.FontStyle]::Bold)
$penGreen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 0, 255, 0), 2)
$penRed = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 255, 60, 60), 2)
$penYellow = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 255, 220, 0), 2)
$penCyan = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 0, 230, 255), 2)
$penWhite = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 240, 240, 240), 2)
$penMagenta = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 255, 0, 255), 2)
$penOrange = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 255, 140, 0), 2)

$brushBg = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(235, 15, 15, 15))
$brushText = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::White)
$brushCenter = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 255, 40, 40))

# 1. Vẽ 2 khung tổng Dòng 1 & Dòng 2
$rowKeys = @("vip5_row_1", "vip5_row_2")
foreach ($rk in $rowKeys) {
    $rElem = $json.elements.$rk
    if ($rElem) {
        $rBox = $rElem.box_567x1014
        $penRow = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 255, 215, 0), 3)
        $penRow.DashStyle = [System.Drawing.Drawing2D.DashStyle]::Dash
        $g.DrawRectangle($penRow, [int]$rBox.x, [int]$rBox.y, [int]$rBox.w, [int]$rBox.h)
        
        $lbl = $rElem.title
        $sz = $g.MeasureString($lbl, $font)
        $g.FillRectangle($brushBg, [int]$rBox.x + 2, [int]$rBox.y - [int]$sz.Height - 3, [int]$sz.Width + 4, [int]$sz.Height + 2)
        $g.DrawString($lbl, $font, $brushText, [float]($rBox.x + 4), [float]($rBox.y - [int]$sz.Height - 2))
    }
}

# 2. Vẽ tất cả các elements còn lại
foreach ($prop in $json.elements.PSObject.Properties) {
    $name = $prop.Name
    if ($name -in $rowKeys) { continue }
    
    $elem = $prop.Value
    $box = $elem.box_567x1014
    if ($box) {
        $pen = $penGreen
        if ($name -eq "tab_1_primary") { $pen = $penWhite }
        elseif ($name -eq "tab_2_vip5_medium") { $pen = $penCyan }
        elseif ($name -eq "tab_3_vip7_advanced") { $pen = $penYellow }
        elseif ($name -eq "tab_4_vip9_superior") { $pen = $penRed }
        elseif ($name -like "*odd*") { $pen = $penCyan }
        elseif ($name -like "*_input") { $pen = $penCyan }
        elseif ($name -like "*_reward") { $pen = $penMagenta }
        
        [int]$bx = [int]$box.x
        [int]$by = [int]$box.y
        [int]$bw = [int]$box.w
        [int]$bh = [int]$box.h
        
        $rect = New-Object System.Drawing.Rectangle($bx, $by, $bw, $bh)
        $g.DrawRectangle($pen, $rect)
        
        # Center Point
        [int]$cx = $bx + [int]($bw / 2)
        [int]$cy = $by + [int]($bh / 2)
        $g.FillEllipse($brushCenter, $cx - 4, $cy - 4, 8, 8)
        
        # Label Text Background
        $label = if ($elem.title) { $elem.title } else { $name }
        $textSize = $g.MeasureString($label, $font)
        [int]$tw = [int]$textSize.Width + 4
        [int]$th = [int]$textSize.Height + 2
        
        [int]$tx = $bx
        [int]$ty = $by - $th - 2
        
        if ($name -eq "tab_1_primary") { $ty = $by - $th - 2; $tx = $bx - 2 }
        elseif ($name -eq "tab_2_vip5_medium") { $ty = $by + $bh + 3; $tx = $bx - 5 }
        elseif ($name -eq "tab_3_vip7_advanced") { $ty = $by - $th - 2; $tx = $bx - 5 }
        elseif ($name -eq "tab_4_vip9_superior") { $ty = $by + $bh + 3; $tx = [Math]::Min($bx - 15, 560 - $tw) }
        elseif ($name -eq "btn_odd") { $ty = $by - $th - 2; $tx = $bx }
        elseif ($name -eq "btn_even") { $ty = $by + $bh + 3; $tx = $bx }
        elseif ($name -like "vip5_row_*_input") { $ty = $by + $bh + 4; $tx = $bx }
        elseif ($name -like "vip5_row_*_reward") { $ty = $by + $bh + 4; $tx = [Math]::Max(2, [Math]::Min($bx - 5, 560 - $tw)) }
        elseif ($ty -lt 2) { $ty = $by + $bh + 2 }
        
        $bgRect = New-Object System.Drawing.Rectangle([int]$tx, [int]$ty, $tw, $th)
        $g.FillRectangle($brushBg, $bgRect)
        $g.DrawString($label, $font, $brushText, [float]($tx + 2), [float]($ty + 1))
    }
}

$g.Dispose()
$bmp.Save($outPath, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output "SUCCESS: $outPath"
