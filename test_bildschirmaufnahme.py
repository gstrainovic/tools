"""Verhalten von bildschirmaufnahme: nimmt in Stücken auf, nummeriert die Dateien, stoppt sauber bei SIGINT."""
import os
import signal
import threading
import unittest

from gi.repository import GLib

import bildschirmaufnahme


class FalscherProxy:
    """Spielt org.gnome.Shell.Screencast: merkt sich Start- und Stopp-Aufrufe mit Dateinamen."""

    def __init__(self):
        self.aufrufe = []

    def call_sync(self, methode, parameter, *_):
        if methode == "Screencast":
            datei, optionen = parameter.unpack()
            self.aufrufe.append(("start", datei, optionen["framerate"]))
            return GLib.Variant("(bs)", (True, datei + ".mp4"))
        self.aufrufe.append(("stop",))
        return GLib.Variant("(b)", (True,))


class Stuecke(unittest.TestCase):
    def test_nimmt_in_nummerierten_stuecken_auf_und_stoppt_bei_sigint(self):
        proxy = FalscherProxy()
        # Stücke starten bei 0, 1.3 und 2.6 s (je 1 s plus 0.3 s Pause); Abbruch mitten im dritten
        threading.Timer(3.1, lambda: os.kill(os.getpid(), signal.SIGINT)).start()
        bildschirmaufnahme.main(["/tmp/x/meeting", "--stueck", "1", "--fps", "7"], proxy=proxy)
        starts = [a for a in proxy.aufrufe if a[0] == "start"]
        self.assertEqual([a[1] for a in starts], ["/tmp/x/meeting-000", "/tmp/x/meeting-001", "/tmp/x/meeting-002"])
        self.assertTrue(all(a[2] == 7 for a in starts))
        self.assertEqual(proxy.aufrufe[-1], ("stop",), "letztes Stück wird beim Beenden abgeschlossen")
        self.assertEqual(sum(1 for a in proxy.aufrufe if a[0] == "stop"), 3)


if __name__ == "__main__":
    unittest.main()
