# SplitTxtFile.ps1
param (
    [Parameter(Mandatory = $true)]
    [string]$InputFile,

    [Parameter(Mandatory = $false)]
    [int64]$ChunkSizeMB = 10
)

# Calculate chunk size in bytes
$ChunkSize = $ChunkSizeMB * 1MB
$BaseName = [System.IO.Path]::GetFileNameWithoutExtension($InputFile)
$Extension = [System.IO.Path]::GetExtension($InputFile)
$OutputDir = [System.IO.Path]::GetDirectoryName($InputFile)

# Open the file for reading
$reader = [System.IO.StreamReader]::new($InputFile)
$chunkIndex = 1
$chunkBytes = 0
$writer = $null

try {
    while (($line = $reader.ReadLine()) -ne $null) {
        $lineBytes = [System.Text.Encoding]::UTF8.GetByteCount($line + "`r`n")

        # Create a new chunk if it doesn't exist or if this line would exceed the limit
        if (-not $writer -or ($chunkBytes + $lineBytes) -gt $ChunkSize) {
            if ($writer) {
                $writer.Close()
            }

            $outputFile = Join-Path $OutputDir ("{0}_part{1}{2}" -f $BaseName, $chunkIndex, $Extension)
            $writer = [System.IO.StreamWriter]::new($outputFile, $false, [System.Text.Encoding]::UTF8)
            Write-Host "Creating $outputFile..."
            $chunkIndex++
            $chunkBytes = 0
        }

        # Write the line and update byte count
        $writer.WriteLine($line)
        $chunkBytes += $lineBytes
    }
}
finally {
    if ($writer) { $writer.Close() }
    if ($reader) { $reader.Close() }
}

Write-Host "Splitting complete. Created $($chunkIndex - 1) chunk(s)."
