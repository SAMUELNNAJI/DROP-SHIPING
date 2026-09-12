$c = Get-Content -Path 'index.html'
$start = 935
$end = 1000
for ($i = $start; $i -le $end; $i++) {
    Write-Output "$($i+1): $($c[$i])"
}