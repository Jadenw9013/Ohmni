param(
    [Parameter(Mandatory = $true)][string[]]$Urls,
    [string]$RunDirectory = 'out/component-behavior/run'
)

# Use the normal Windows trust store; certificate verification stays enabled.
$ErrorActionPreference = 'Stop'
$runRoot = [IO.Path]::GetFullPath($RunDirectory)
$archiveRoot = Join-Path $runRoot 'fetched-sources'
[IO.Directory]::CreateDirectory($archiveRoot) | Out-Null
$utf8 = [Text.UTF8Encoding]::new($false)
foreach ($sourceUrl in $Urls) {
    $downloadPath = Join-Path $archiveRoot ([guid]::NewGuid().ToString() + '.download')
    $receipt = [ordered]@{
        url = $sourceUrl
        request_url = $sourceUrl
        timestamp = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
        http_status = $null
        content_sha256 = $null
        content_bytes = 0
        tool_used = 'tools.behavior_audit.fetch_sources_windows/Invoke-WebRequest'
        error = $null
    }
    try {
        $response = Invoke-WebRequest -Uri $sourceUrl -OutFile $downloadPath -PassThru -TimeoutSec 30
        $receipt.http_status = [int]$response.StatusCode
        $receipt.content_sha256 = (Get-FileHash -LiteralPath $downloadPath -Algorithm SHA256).Hash.ToLowerInvariant()
        $receipt.content_bytes = (Get-Item -LiteralPath $downloadPath).Length
        Copy-Item -LiteralPath $downloadPath -Destination (Join-Path $archiveRoot ($receipt.content_sha256 + '.bin')) -Force
    } catch {
        $receipt.error = $_.Exception.Message
        if ($_.Exception.Response) { $receipt.http_status = [int]$_.Exception.Response.StatusCode }
    } finally {
        if (Test-Path -LiteralPath $downloadPath) { Remove-Item -LiteralPath $downloadPath }
    }
    $json = $receipt | ConvertTo-Json -Compress
    [IO.File]::AppendAllText((Join-Path $runRoot 'FETCH_LEDGER.jsonl'), $json + "`n", $utf8)
    Write-Output $json
}
