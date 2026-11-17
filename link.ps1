# link.ps1 — Windows-Gegenstück zum Skill-Teil von link.sh, idempotent, ohne Administratorrechte:
#   Claude-Skills (skills\<name>\ und ~\projects\skills-privat\skills\<name>\) als Junction nach ~\.claude\skills\<name>.
# ~\.claude\skills ist selbst eine Junction auf das Repo claude-config; die Namen kommen darum in dessen
# .git\info\exclude, damit die fremden Skills dort nicht versioniert werden.
# Aufruf: powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\projects\tools\link.ps1
# (Profil g.strainovic.WA: Repos liegen unter C:\Users\g.strainovic\projects, darum -Projekte.)
#   Dazu Starter für Git-Bash in ~\.local\bin (steht dort im PATH), Gegenstück zu den Verweisen aus link.sh:
#   Windows kennt keine ausführbaren Verweise, darum je Befehl ein kleines Bash-Skript, das das Werkzeug startet.
param(
    [string]$Projekte = 'C:\Users\g.strainovic\projects',
    [string]$SkillDir = "$env:USERPROFILE\.claude\skills",
    [string]$BinDir = "$env:USERPROFILE\.local\bin"
)
$ErrorActionPreference = 'Stop'

$tools = ($Projekte -replace '\\', '/') + '/tools'
$starter = [ordered]@{
    'gsc'                     = "exec uv run --script `"$tools/gsc.py`" `"`$@`""
    'ads'                     = "exec uv run --script `"$tools/ads.py`" `"`$@`""
    'bing'                    = "exec uv run --script `"$tools/bing.py`" `"`$@`""
    'fragen'                  = "exec python `"$tools/fragen.py`" `"`$@`""
    'chrome-anhaengen'        = "exec python `"$tools/chrome_anhaengen.py`" `"`$@`""
    'wartungsheft-cost-watch' = "exec bash `"$tools/wartungsheft-cost-watch.sh`" `"`$@`""
    # Zugänge auf dem PC nur aus find-jobs\.secrets (AGENTS.md von find-jobs, «Windows-PC»)
    'mailbox'                 = "m=`"$($Projekte -replace '\\', '/')/find-jobs/.secrets/mailbox`"`n" +
                                "[ -f `"`$m`" ] && exec bash `"`$m`" `"`$@`"`nexec python `"$tools/mailbox.py`" `"`$@`""
}
New-Item -ItemType Directory -Force $BinDir | Out-Null
$utf8 = New-Object System.Text.UTF8Encoding($false)
foreach ($name in $starter.Keys) {
    $text = "#!/usr/bin/env bash`n# angelegt von tools/link.ps1`n$($starter[$name])`n"
    $dst = Join-Path $BinDir $name
    if ((Test-Path $dst) -and ([IO.File]::ReadAllText($dst) -eq $text)) { Write-Output "vorhanden: $dst"; continue }
    [IO.File]::WriteAllText($dst, $text, $utf8)
    Write-Output "Starter: $dst"
}

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
