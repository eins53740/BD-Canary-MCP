# merge-json.ps1
# Description: Merges all JSON files in the current directory into one combined JSON file.

param (
    [string]$SourceFolder = ".",
    [string]$OutputFile = "merged.json"
)

# Get all JSON files from the folder
$jsonFiles = Get-ChildItem -Path $SourceFolder -Filter "*.json"

# Initialize an empty array to hold the JSON content
$mergedContent = @()

foreach ($file in $jsonFiles) {
    try {
        # Read and parse each JSON file
        $content = Get-Content -Path $file.FullName -Raw | ConvertFrom-Json
        $mergedContent += $content
        Write-Host "Merged: $($file.Name)"
    }
    catch {
        Write-Warning "Failed to read or parse $($file.Name): $_"
    }
}

# Convert the merged array back to JSON and save
$mergedJson = $mergedContent | ConvertTo-Json -Depth 100
Set-Content -Path (Join-Path $SourceFolder $OutputFile) -Value $mergedJson -Encoding UTF8

Write-Host "✅ All JSON files merged successfully into '$OutputFile'"
