<#
Search Console: «Indexierung beantragen» für eine oder mehrere URLs, nacheinander, je mit Bestätigung.
Die API kennt keinen Indexierungsantrag, darum über die Oberfläche in Gorans Chrome (Skill browser-wahl).

Voraussetzung: Session gchrome hängt an und ist sichtbar (nur nach Gorans Ja):
    python3 ~\projects\tools\chrome_anhaengen.py --zeigen
Aufruf:
    pwsh ~\projects\tools\gsc_indexierung.ps1 -Domain example.ch -Url https://example.ch/a, https://example.ch/b
Danach: python3 ~\projects\tools\chrome_anhaengen.py --verstecken

Bricht bei der ersten URL ohne Bestätigung ab (Kontingent erschöpft, Knopf fehlt) und meldet den Seitentext.
Den Lauf im Vordergrund starten: Ein abgebrochener playwright-cli-Aufruf läuft im Browser weiter, bis sein Tab
geschlossen ist (playwright-cli -s=gchrome tab-list, dann tab-close <Nummer>).
#>
param(
    [Parameter(Mandatory)][string]$Domain,
    [Parameter(Mandatory)][string[]]$Url
)
# Mit pwsh -File kommt eine Liste als ein Text an: an Kommas trennen.
$Url = $Url | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim().Trim("'", '"') } | Where-Object { $_ }
$vorlage = Get-Content -Raw -Encoding utf8 (Join-Path $PSScriptRoot 'gsc_indexierung.js')
$datei = Join-Path ([IO.Path]::GetTempPath()) 'gsc_indexierung_lauf.js'
$fehler = 0
foreach ($u in $Url) {
    $js = $vorlage.Replace('__URL__', $u).Replace('__DOMAIN__', $Domain)
    [IO.File]::WriteAllText($datei, $js, [Text.UTF8Encoding]::new($false))
    $r = playwright-cli -s=gchrome run-code --filename $datei 2>&1 | Out-String
    if ($r -match '"ergebnis":"([^"]*)"') { $erg = $Matches[1] } else { $erg = 'UNKLAR: ' + $r.Substring(0, [Math]::Min(400, $r.Length)) }
    "$erg  <=  $u"
    if ($erg -notmatch 'wurde beantragt') { $fehler = 1; break }
}
Remove-Item $datei -ErrorAction SilentlyContinue
exit $fehler
