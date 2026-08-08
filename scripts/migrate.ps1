# Convenience wrapper for Windows PowerShell.
# Usage (from rag-api root):
#   .\scripts\migrate.ps1
#   .\scripts\migrate.ps1 current
#   .\scripts\migrate.ps1 downgrade -1

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$MigrateArgs
)

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not $MigrateArgs -or $MigrateArgs.Count -eq 0) {
    poetry run python scripts/migrate.py upgrade head
} else {
    poetry run python scripts/migrate.py @MigrateArgs
}
