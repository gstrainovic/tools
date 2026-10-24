// Läuft vor jedem Seitenskript (document_start, MAIN world): Die Seite kann keinen beforeunload-Handler mehr
// registrieren, Chrome zeigt darum nie «Website verlassen?». Drei Wege, die Seiten dafür nutzen, werden abgefangen.
(() => {
  const ist = (typ) => String(typ).toLowerCase() === "beforeunload";

  // 1. addEventListener('beforeunload', …) auf window, document oder Elementen
  const original = EventTarget.prototype.addEventListener;
  EventTarget.prototype.addEventListener = function (typ, ...rest) {
    if (ist(typ)) return;
    return original.call(this, typ, ...rest);
  };

  // 2. window.onbeforeunload = … (Zuweisung läuft ins Leere)
  Object.defineProperty(window, "onbeforeunload", {
    configurable: true,
    get: () => null,
    set: () => {},
  });

  // 3. Handler, die trotzdem durchkommen (etwa über Frames): Ereignis sofort stoppen, ohne returnValue
  original.call(window, "beforeunload", (e) => e.stopImmediatePropagation(), true);
})();
