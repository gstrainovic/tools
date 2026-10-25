// Sucht auf temu.com/ch über Startseite und Suchfeld und gibt die Trefferliste mit Preis und Link zurück; nur mit
// einer Temu-ID (__ID__, aus einem Link von Goran) klickt es diesen einen Treffer an und liest die Produktseite.
// Direktaufrufe von Produkt-URLs (goods.html, /ch/…-g-…html) lösen Captchas aus, Produktseiten manchmal auch.
// Platzhalter __Q__ ersetzt temu_produkt.sh durch den Suchbegriff (kurz, zwei bis vier Wörter).
async page => {
  const q = '__Q__';
  const captcha = t => /Überprüfung|Sicherheitsüberprüfung|verify you are|Captcha|Schieberegler/i.test(t);
  await page.bringToFront();
  await page.goto('https://www.temu.com/ch', {waitUntil: 'load', timeout: 90000});
  await page.waitForTimeout(5000);
  let body = (await page.locator('body').innerText()).replace(/​/g, '');
  if (captcha(body.slice(0, 3000))) return 'CAPTCHA Startseite';
  const sf = page.locator('input[type="search"], input[role="combobox"], input[placeholder*="uch"], input[id*="search"]').first();
  // Kein click(): Ein Overlay macht das Feld für Playwright «nicht stabil», fill mit force geht trotzdem.
  await sf.focus();
  await sf.fill(q, {force: true});
  await sf.press('Enter');
  await page.waitForTimeout(9000);
  body = (await page.locator('body').innerText()).replace(/​/g, '');
  if (captcha(body.slice(0, 3000))) return 'CAPTCHA Trefferliste';
  // Ohne Temu-ID (g-… aus einem Link von Goran) wird nichts angeklickt: Die Trefferliste mit Preis und Link ist
  // das Ergebnis. Nur mit ID öffnet das Skript genau diesen Artikel.
  const id = '__ID__';
  const links = await page.$$('a[href*="-g-"]');
  const treffer = [];
  let ziel = null;
  for (const a of links) {
    const txt = (await a.evaluate(e => e.parentElement.parentElement.parentElement.innerText)).replace(/\s+/g, ' ');
    const href = await a.getAttribute('href');
    const preis = txt.match(/CHF ?[\d'.]+/);
    if (!preis) continue;
    const gid = (href.match(/-g-(\d+)\.html/) || [])[1] || '?';
    treffer.push(preis[0] + ' | g-' + gid + ' | ' + txt.replace(/CHF ?[\d'.]+.*$/, '').slice(0, 110));
    if (!ziel && id && href.includes('-g-' + id + '.html')) ziel = a;
  }
  if (!id) return 'TREFFERLISTE (Preis je Kachel, ohne ID wird nichts geöffnet):\n' + [...new Set(treffer)].slice(0, 15).join('\n');
  if (!ziel) return 'KEIN TREFFER mit diesem Link (g-' + id + '); Trefferliste:\n' + [...new Set(treffer)].slice(0, 15).join('\n');
  // Kein scrollIntoViewIfNeeded(): Temus Seite ist für Playwright nie «stabil» (Animationen).
  await ziel.evaluate(e => e.scrollIntoView({block: 'center'}));
  await page.waitForTimeout(1500);
  const box = await ziel.boundingBox();
  const warte = page.context().waitForEvent('page', {timeout: 15000}).catch(() => null);
  // Ohne boundingBox (Link unsichtbar, nur das Bild ist klickbar) den Klick im Seitenskript auslösen.
  if (box) await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  else await ziel.evaluate(e => e.click());
  const neu = await warte;
  const p = neu || page;
  await p.waitForLoadState('load').catch(() => {});
  await p.waitForTimeout(9000);
  const t = (await p.locator('body').innerText()).replace(/​/g, '').replace(/\s+/g, ' ');
  if (captcha(t.slice(0, 3000))) return 'CAPTCHA Produktseite ' + p.url();
  const h1 = await p.locator('h1').first().innerText().catch(() => '');
  // Produktpreis steht nach dem Titel; der erste CHF-Treffer im Text ist der Warenkorb.
  const start = Math.max(0, t.indexOf(h1.slice(0, 40)));
  const i = start + t.slice(start).search(/CHF ?\d/);
  const out = 'URL: ' + p.url().replace(/\?.*/, '') + '\nTitel: ' + h1.slice(0, 220) + '\nPreis: ' + t.slice(i, i + 900);
  if (neu) await neu.close();
  return out;
}
