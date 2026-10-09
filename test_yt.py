import argparse
import importlib.util
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

spec = importlib.util.spec_from_file_location("yt", Path(__file__).with_name("yt.py"))
yt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(yt)

ANALYTICS = {
    "columnHeaders": [{"name": "video"}, {"name": "views"}, {"name": "estimatedMinutesWatched"},
                      {"name": "averageViewDuration"}, {"name": "subscribersGained"}],
    "rows": [["Pv4ugkC5yWU", 40, 25, 38, 1], ["gVyuTsk_LrI", 3, 2, 30, 0]],
}


class Scopes(unittest.TestCase):
    def test_login_fragt_auch_youtube_analytics_an(self):
        self.assertIn("https://www.googleapis.com/auth/youtube.force-ssl", yt.SCOPES)
        self.assertIn("https://www.googleapis.com/auth/yt-analytics.readonly", yt.SCOPES)


class Stats(unittest.TestCase):
    def test_zeigt_aufrufe_je_video_mit_titel(self):
        analytics = mock.MagicMock()
        analytics.reports().query().execute.return_value = ANALYTICS
        titles = {"Pv4ugkC5yWU": "Fuhrpark im Griff #shorts", "gVyuTsk_LrI": "Serviceheft digital"}
        out = io.StringIO()
        with mock.patch.object(yt, "analytics_service", return_value=analytics), \
             mock.patch.object(yt, "video_titles", return_value=titles), redirect_stdout(out):
            yt.cmd_stats(argparse.Namespace(channel="UCejZg-WBrGzth2W-sLYCNzA", days=28))
        text = out.getvalue()
        self.assertIn("Pv4ugkC5yWU\t40\t25\t38\t1\tFuhrpark im Griff #shorts", text)
        self.assertIn("gVyuTsk_LrI\t3\t2\t30\t0\tServiceheft digital", text)

    def test_fragt_den_zeitraum_fuer_den_kanal_ab(self):
        analytics = mock.MagicMock()
        analytics.reports().query().execute.return_value = {"rows": []}
        with mock.patch.object(yt, "analytics_service", return_value=analytics), \
             mock.patch.object(yt, "video_titles", return_value={}), redirect_stdout(io.StringIO()):
            yt.cmd_stats(argparse.Namespace(channel="UCejZg-WBrGzth2W-sLYCNzA", days=7))
        kwargs = analytics.reports().query.call_args.kwargs
        self.assertEqual(kwargs["ids"], "channel==UCejZg-WBrGzth2W-sLYCNzA")
        self.assertEqual(kwargs["dimensions"], "video")
        self.assertIn("views", kwargs["metrics"])


if __name__ == "__main__":
    unittest.main()
