param([Parameter(Mandatory=$true)][string]$CommitSha)

gh workflow run deploy.yml --ref main -f "ref=$CommitSha"
if ($LASTEXITCODE -ne 0) { throw "Rollback workflow was not started" }
Write-Host "Rollback deployment requested for $CommitSha"
