<#
.SYNOPSIS
Publishes the CMO Bridge wiki-source Markdown pages to the GitHub Wiki.
Requires Git, GitHub push credentials, and the Wiki's first Home page already saved.
Does not force push or remove unrelated existing pages.
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$remote = 'https://github.com/jheinrichk/Command-Modern-Operations-CMO-LLM-Bridge.wiki.git'
$temp = Join-Path ([System.IO.Path]::GetTempPath()) ('cmo-bridge-wiki-' + [guid]::NewGuid().ToString('N'))

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'Git is not installed or is not available on PATH.'
}

try {
    Write-Host 'Cloning the GitHub Wiki...'
    & git clone --depth 1 $remote $temp
    if ($LASTEXITCODE -ne 0) {
        throw 'Wiki clone failed. Save the first Home page in the browser before running this script.'
    }

    $pages = Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*.md' -File |
        Where-Object { $_.Name -ne 'PUBLISHING.md' }

    foreach ($page in $pages) {
        Copy-Item -LiteralPath $page.FullName -Destination (Join-Path $temp $page.Name) -Force
        & git -C $temp add -- $page.Name
        if ($LASTEXITCODE -ne 0) { throw "Could not stage $($page.Name)." }
    }

    $changed = @(& git -C $temp diff --cached --name-only)
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect staged Wiki changes.' }
    if ($changed.Count -eq 0) {
        Write-Host 'Wiki pages already match the prepared source. Nothing to publish.'
        return
    }

    Write-Host 'Publishing the following pages:'
    $changed | ForEach-Object { Write-Host "  $_" }
    & git -C $temp commit -m 'Publish CMO LLM Bridge documentation and scenario showcase'
    if ($LASTEXITCODE -ne 0) {
        throw 'Commit failed. Check Git author name and email configuration.'
    }
    & git -C $temp push origin HEAD
    if ($LASTEXITCODE -ne 0) {
        throw 'Push failed. Check your GitHub permissions/credentials and retry after reviewing any remote changes.'
    }

    Write-Host 'Wiki published: https://github.com/jheinrichk/Command-Modern-Operations-CMO-LLM-Bridge/wiki'
}
finally {
    if (Test-Path -LiteralPath $temp) {
        Remove-Item -LiteralPath $temp -Recurse -Force
    }
}
