---
name: doku-pflege
description: Regeln für todo.md, AGENTS.md, CLAUDE.md, README und Memories: nur geltender Stand, kein Changelog, Falsches löschen, Auslagern in Skills. Laden, bevor eine dieser Dateien geschrieben oder geändert wird.
---

# Doku-Pflege (alle Projekte, verbindlich)

## todo.md

- **Erledigt = löschen:** Ist eine todo.md komplett abgearbeitet, wird die Datei gelöscht (git rm + commit), nicht als "erledigt" stehen gelassen.
- **Kein Changelog:** todo.md enthält nur offene Punkte. Erledigt-Logs, Datumsvermerke und "umgesetzt am"-Abschnitte haben dort nichts verloren, dafür gibt es die Git-History.
- **Wissen nach AGENTS.md:** Learnings, bekannte Grenzen, Workflows und Architektur-Entscheidungen gehören in die AGENTS.md des Projekts, nicht in todo.md.

## AGENTS.md und CLAUDE.md

- **Auch hier kein Changelog:** AGENTS.md und CLAUDE.md beschreiben den *aktuellen* Stand. Kein "vorher war X", kein "geändert am TT.MM.JJJJ", kein "aufgefallen am", keine Erledigt-Vermerke. Wer wissen will, wie es früher war, liest `git log`.
- **Datum nur wenn es die Gegenwart erklärt:** z. B. "auf 0.15.2 gepinnt, Migration auf 0.16 ist ein eigener Meilenstein". Ein Datum, das nur festhält *wann* etwas passierte, kommt raus.
- **Ein Eintrag = eine geltende Regel oder Tatsache.** Die Begründung darf mit, aber in einem Satz und im Präsens. Die Leidensgeschichte gehört in die Commit-Message.
- **Falsches und Nutzloses löschen, nicht markieren.** Stellt sich ein Eintrag (Konkurrent, Zahl, Feature, Fussnote) als falsch oder unnütz heraus, kommt er weg, samt Querverweisen. Kein «gibt es nicht», kein «kein Konkurrent», kein «vorerst gestrichen». Der Grund steht in der Commit-Message. Gilt für Businessplan, todo.md, AGENTS.md, CLAUDE.md, README und Memories.
- **Wächst die Datei über ein paar Bildschirme, auslagern:** zusammenhängende Themen als Skill unter `.claude/skills/<name>/SKILL.md`, damit sie beim passenden Anlass automatisch greifen statt nur beim Durchlesen. In AGENTS.md bleibt ein Zweizeiler mit Verweis. Themen, die mehrere Repos teilen, kommen als User-Skill nach `~/projects/tools/skills/<name>/SKILL.md` (verknüpft nach `~/.claude/skills/` per `link.sh`).
