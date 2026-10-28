# link.ps1 — Windows-Gegenstück zum Skill-Teil von link.sh, idempotent, ohne Administratorrechte:
#   Claude-Skills (skills\<name>\ und ~\projects\skills-privat\skills\<name>\) als Junction nach ~\.claude\skills\<name>.
# ~\.claude\skills ist selbst eine Junction auf das Repo claude-config; die Namen kommen darum in dessen
# .git\info\exclude, damit die fremden Skills dort nicht versioniert werden.
# Aufruf: powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\projects\tools\link.ps1
# (Profil g.strainovic.WA: Repos liegen unter C:\Users\g.strainovic\projects, darum -Projekte.)
param(
    [string]$Projekte = 'C:\Users\g.strainovic\projects',
    [string]$SkillDir = "$env:USERPROFILE\.claude\skills"
)
$ErrorActionPreference = 'Stop'

$quellen = @("$Projekte\tools\skills", "$Projekte\skills-privat\skills") | Where-Object { Test-Path $_ }
$ziel = (Get-Item $SkillDir).Target | Select-Object -First 1
$exclude = $null
if ($ziel) {
    $git = Join-Path $ziel '..\.git\info\exclude'
    if (Test-Path $git) { $exclude = (Resolve-Path $git).Path }
}

foreach ($q in $quellen) {
    foreach ($d in Get-ChildItem $q -Directory) {
        if (-not (Test-Path (Join-Path $d.FullName 'SKILL.md'))) { continue }
        $dst = Join-Path $SkillDir $d.Name
        if (Test-Path $dst) {
            $item = Get-Item $dst -Force
            if ($item.LinkType -ne 'Junction') {
                Write-Warning "übersprungen: $dst ist ein Ordner, keine Verknüpfung, bitte von Hand prüfen"
                continue
            }
            if ($item.Target -contains $d.FullName) { Write-Output "vorhanden: $dst"; continue }
            cmd /c rmdir "$dst" | Out-Null
        }
        cmd /c mklink /J "$dst" "$($d.FullName)" | Out-Null
        Write-Output "$dst -> $($d.FullName)"
        if ($exclude) {
            $zeile = "skills/$($d.Name)"
            if (-not (Select-String -Path $exclude -SimpleMatch -Pattern $zeile -Quiet)) {
                Add-Content -Path $exclude -Value $zeile -Encoding utf8
            }
        }
    }
}
