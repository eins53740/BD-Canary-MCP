$infile = "C:\Users\bfsd\Desktop\mcp debug aux\points\ignition.json"
$outdir = "C:\Users\bfsd\Desktop\mcp debug aux"
$linesPerFile = 250000
$i = 1
Get-Content $infile -ReadCount $linesPerFile | ForEach-Object {
    $outfile = "{0}\part_Ignition_{1}.json" -f $outdir, $i
    $_ | Set-Content $outfile
    $i++
}
