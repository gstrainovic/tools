// Search Console: für eine URL «Indexierung beantragen» und die Bestätigung abwarten.
// Aufruf nur über gsc_indexierung.ps1, das __URL__ und __DOMAIN__ ersetzt.
// Eigener Tab je Aufruf; Rückgabe { url, ergebnis, log } mit dem Text der Seite je Schritt.
async page => {
  const url = '__URL__';
  const domain = '__DOMAIN__';
  const tab = await page.context().newPage();
  const log = [];
  const zustand = async () => {
    const t = await tab.locator('body').innerText();
    return (t.match(/Indexierung (wurde )?beantragt[^\n]*|Es wird getestet[^\n]*|Kontingent[^\n]*|Fehler[^\n]*|URL ist (nicht )?auf Google[^\n]*/gi) || []).join(' | ');
  };
  try {
    await tab.goto(`https://search.google.com/search-console?resource_id=sc-domain%3A${domain}`, { waitUntil: 'load' });
    await tab.waitForTimeout(4000);
    await tab.bringToFront();
    const feld = tab.locator(`input[aria-label="Jede URL unter ${domain} prüfen"]`).first();
    await feld.click({ force: true });
    await feld.fill(url, { force: true });
    log.push('Feld: ' + (await feld.inputValue()).length + ' Zeichen');
    await feld.press('Enter');
    try {
      await tab.waitForURL(/inspect\?.*id=/, { timeout: 60000 });
    } catch (e) {
      return { url, ergebnis: 'Prüfung startet nicht', log, text: (await tab.locator('body').innerText()).slice(0, 400) };
    }
    let p = null;
    for (let i = 0; i < 20 && !p; i++) {
      await tab.waitForTimeout(2000);
      p = await tab.evaluate(() => {
        const e = [...document.querySelectorAll('span')].find(x => /^indexierung beantragen$/i.test(x.textContent.trim()) && x.getBoundingClientRect().width > 0);
        if (!e) return null;
        const r = e.getBoundingClientRect();
        return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
      });
    }
    if (!p) return { url, ergebnis: 'Knopf nicht gefunden', log, text: await zustand() };
    log.push('vor Klick: ' + await zustand());
    await tab.mouse.click(p.x, p.y);
    // Der Livetest dauert laut Google «ein oder zwei Minuten», einmal mehr als 150 s.
    for (let s = 0; s < 240; s += 5) {
      await tab.waitForTimeout(5000);
      const z = await zustand();
      if (/beantragt|Kontingent|Fehler/i.test(z)) { log.push(s + 's: ' + z); return { url, ergebnis: z, log }; }
      if (s % 30 === 0) log.push(s + 's: ' + z);
    }
    return { url, ergebnis: 'keine Bestätigung nach 240 s', log };
  } finally {
    await tab.close();
  }
}
