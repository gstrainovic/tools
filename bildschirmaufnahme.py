#!/usr/bin/env python3
"""
bildschirmaufnahme: ganzen Bildschirm über GNOME Shell aufnehmen (D-Bus org.gnome.Shell.Screencast, kein Dialog,
h264 in mp4), ohne Ton (den nimmt `mithoeren --ton` auf). Gedacht für Online-Meetings, in denen das Gegenüber den
Bildschirm teilt: Claude Code zieht aus fertigen Stücken Standbilder (`ffmpeg -ss <s> -i <stück> -frames:v 1 bild.png`).

  bildschirmaufnahme ~/Dokumente/meeting-kunde            # schreibt meeting-kunde-000.mp4, -001.mp4, …
  bildschirmaufnahme ~/Dokumente/meeting-kunde --stueck 60 --fps 5

Die Aufnahme läuft in Stücken (Standard 60 s), weil GNOME das mp4 erst beim Stoppen abschliesst; nur fertige Stücke
sind lesbar. Zwischen zwei Stücken fehlt rund eine Sekunde. Die D-Bus-Verbindung bleibt offen, bis Strg+C oder
SIGTERM kommt; ein einzelner `gdbus call` bricht sofort ab («Sender has vanished»). GNOME erlaubt Dritten keine
Einzelbilder per D-Bus (org.gnome.Shell.Screenshot: «Screenshot is not allowed»), darum Video statt Fotos.
"""
import argparse
import signal
import sys

from gi.repository import Gio, GLib


def gnome_proxy():
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    return Gio.DBusProxy.new_sync(bus, Gio.DBusProxyFlags.NONE, None, "org.gnome.Shell.Screencast",
                                  "/org/gnome/Shell/Screencast", "org.gnome.Shell.Screencast", None)


def main(argv=None, proxy=None):
    p = argparse.ArgumentParser(description="Bildschirm in mp4-Stücken aufnehmen")
    p.add_argument("praefix", help="Pfad ohne Endung, Stücke heissen <praefix>-NNN.mp4")
    p.add_argument("--stueck", type=int, default=60, help="Länge je Stück in Sekunden (Standard 60)")
    p.add_argument("--fps", type=int, default=5, help="Bilder je Sekunde (Standard 5)")
    a = p.parse_args(argv)

    proxy = proxy or gnome_proxy()
    loop = GLib.MainLoop()
    zustand = {"nr": 0, "laeuft": False, "ende": False}

    def start():
        if zustand["ende"]:
            return False
        datei = f"{a.praefix}-{zustand['nr']:03d}"
        optionen = {"framerate": GLib.Variant("i", a.fps), "draw-cursor": GLib.Variant("b", True)}
        ok, name = proxy.call_sync("Screencast", GLib.Variant("(sa{sv})", (datei, optionen)),
                                   Gio.DBusCallFlags.NONE, -1, None).unpack()
        if not ok:
            print("Aufnahme nicht gestartet", file=sys.stderr, flush=True)
            loop.quit()
            return False
        zustand["laeuft"] = True
        print("Stück", name, flush=True)
        GLib.timeout_add(a.stueck * 1000, naechstes)  # nicht timeout_add_seconds: das rundet bis zu 1 s auf
        return False

    def stop():
        if zustand["laeuft"]:
            proxy.call_sync("StopScreencast", None, Gio.DBusCallFlags.NONE, -1, None)
            zustand["laeuft"] = False
            zustand["nr"] += 1

    def naechstes():
        stop()
        GLib.timeout_add(300, start)
        return False

    def beenden(*_):
        zustand["ende"] = True
        stop()
        loop.quit()

    signal.signal(signal.SIGINT, beenden)
    signal.signal(signal.SIGTERM, beenden)
    GLib.idle_add(start)
    loop.run()


if __name__ == "__main__":
    main()
