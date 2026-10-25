// Öffnet auf temu.com/ch einen Artikel so, wie Temu es ohne Captcha zulässt: Startseite, Suchfeld, Enter,
// Treffer per Mausklick. Direktaufrufe von Produkt-URLs (goods.html, /ch/…-g-…html) lösen Captchas aus.
// Platzhalter __Q__ ersetzt temu_produkt.sh durch den Suchbegriff (am besten der Produktname von Temu).
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
  const key = q.toLowerCase().replace(/[^a-zäöü0-9]/g, '').slice(0, 24);
  const links = await page.$$('a[href*="-g-"]');
  const treffer = [];
  let ziel = null;
  for (const a of links) {
    const txt = (await a.evaluate(e => e.parentElement.parentElement.parentElement.innerText)).replace(/\s+/g, ' ');
    const href = await a.getAttribute('href');
    if (!/CHF/.test(txt)) continue;
    treffer.push(txt.slice(0, 120) + ' || ' + href.replace(/\?.*/, ''));
    const norm = txt.toLowerCase().replace(/[^a-zäöü0-9]/g, '');
    if (!ziel && norm.includes(key)) ziel = a;
  }
  if (!ziel) return 'KEIN TREFFER mit diesem Namen; Trefferliste:\n' + [...new Set(treffer)].slice(0, 10).join('\n');
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
  const out = 'URL: ' + p.url().replace(/\?.*/, '') + '\nTitel: ' + h1.slice(0, 220) + '\nPreis: ' + t.slice(i, i + 420);
  if (neu) await neu.close();
  return out;
}
