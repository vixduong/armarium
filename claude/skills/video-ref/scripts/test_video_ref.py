"""Self-test for video_ref.py: python3 -I test_video_ref.py (run by armarium bin/check)."""
import importlib.util, json, os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("video_ref", os.path.join(HERE, "video_ref.py"))
vr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vr)


class CheckSource(unittest.TestCase):
    def test_https_url_is_a_url(self):
        self.assertEqual(vr.check_source("https://www.youtube.com/shorts/abc"), ("url", "https://www.youtube.com/shorts/abc"))

    def test_existing_file_is_a_file(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4") as f:
            self.assertEqual(vr.check_source(f.name), ("file", os.path.abspath(f.name)))

    def test_rejects_other_schemes_options_and_empty(self):
        for bad in ["file:///etc/passwd", "-o x", "--exec=rm", "", "ftp://x/y.mp4", "javascript:alert(1)", "/no/such/file.mp4"]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                vr.check_source(bad)


class Slugify(unittest.TestCase):
    def test_vietnamese_title(self):
        self.assertEqual(vr.slugify("Cảnh mở đầu: Đêm Hà Nội!"), "canh-mo-dau-dem-ha-noi")

    def test_no_path_parts_and_never_empty(self):
        self.assertEqual(vr.slugify("../../etc/passwd"), "etc-passwd")
        self.assertEqual(vr.slugify(""), "video")
        self.assertEqual(vr.slugify("!!!"), "video")

    def test_capped_at_60_without_trailing_dash(self):
        s = vr.slugify("ab " * 40)
        self.assertLessEqual(len(s), 60)
        self.assertFalse(s.endswith("-"))

class PickEvenly(unittest.TestCase):
    def test_keeps_first_and_last_spread_evenly(self):
        self.assertEqual(vr.pick_evenly(list(range(10)), 4), [0, 3, 6, 9])

    def test_under_cap_and_edges(self):
        self.assertEqual(vr.pick_evenly([0, 1, 2], 5), [0, 1, 2])
        self.assertEqual(vr.pick_evenly([], 5), [])
        self.assertEqual(vr.pick_evenly([7, 8, 9], 1), [7])

SHOWINFO = "[Parsed_showinfo_0 @ 0x7940c20cc0] n:   0 pts:      0 pts_time:0       duration:      1 duration_time:0.1     fmt:yuv420p cl:unspecified sar:1/1 s:64x64 i:P iskey:1 type:I checksum:CAA63896 plane_checksum:[E7BC104B DE30680F 509EC02D] mean:[81 90 240] stdev:[0.0 0.0 0.0]" + "\n[Parsed_showinfo_1 @ 0x1] n:   1 pts:  76800 pts_time:3.2     duration:  512\nframe=    2 fps=0.0 q=-0.0 size=N/A time=00:00:03.20\n"


class ParseShowinfo(unittest.TestCase):
    def test_reads_every_pts_time(self):
        self.assertEqual(vr.parse_showinfo(SHOWINFO), [0.0, 3.2])

    def test_no_frames(self):
        self.assertEqual(vr.parse_showinfo("frame=0 fps=0\n"), [])

class SrtToText(unittest.TestCase):
    def test_plain_srt_loses_numbers_times_and_tags(self):
        srt = "1\n00:00:01,000 --> 00:00:02,000\n<i>Xin chào</i>\n\n2\n00:00:02,000 --> 00:00:03,000\nBạn khỏe không\n"
        self.assertEqual(vr.srt_to_text(srt), "Xin chào\nBạn khỏe không")

    def test_rolling_auto_subs_keep_each_line_once(self):
        srt = ("1\n00:00:00,000 --> 00:00:01,000\nhello world\n\n"
               "2\n00:00:01,000 --> 00:00:02,000\nhello world\nthis is\n\n"
               "3\n00:00:02,000 --> 00:00:03,000\nthis is\na test\n")
        self.assertEqual(vr.srt_to_text(srt), "hello world\nthis is\na test")

    def test_empty(self):
        self.assertEqual(vr.srt_to_text(""), "")

def three_colour_video(path):
    """6 s at 10 fps: black 1.4 s, white 3.2 s, gray 1.4 s. The cuts at 1.4 s and 4.6 s are off the even-sampling grid,
    and each changes brightness (ffmpeg's scene score reads luma only: pure red to pure green scores 0)."""
    src = ";".join("color=%s:s=160x90:d=%s:r=10[v%d]" % (c, d, i) for i, (c, d) in enumerate([("black", 1.4), ("white", 3.2), ("gray", 1.4)]))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-filter_complex", src + ";[v0][v1][v2]concat=n=3:v=1[out]",
                    "-map", "[out]", "-pix_fmt", "yuv420p", path], check=True)


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg missing")
class LocalFile(unittest.TestCase):
    def test_frames_at_scene_cuts_contact_sheet_and_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            video, out = os.path.join(tmp, "clip.mp4"), os.path.join(tmp, "out")
            three_colour_video(video)
            self.assertEqual(vr.main([video, "--out", out]), 0)
            self.assertTrue(os.path.isfile(os.path.join(out, "index.json")), "no index.json")
            with open(os.path.join(out, "index.json"), encoding="utf-8") as f:
                index = json.load(f)
            times = [fr["t"] for fr in index["frames"]]
            self.assertGreaterEqual(len(times), 6)
            self.assertEqual(times, sorted(times))
            for cut in (1.4, 4.6):
                self.assertTrue(any(abs(t - cut) < 0.1 for t in times), "no frame at the cut at %ss: %s" % (cut, times))
            for fr in index["frames"]:
                self.assertTrue(os.path.isfile(os.path.join(out, fr["file"])))
            self.assertTrue(os.path.getsize(os.path.join(out, "contact.jpg")) > 0)
            self.assertAlmostEqual(index["duration"], 6.0, delta=0.2)

@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg missing")
class MissingTool(unittest.TestCase):
    def test_link_without_yt_dlp_exits_3_and_leaves_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            bindir, out = os.path.join(tmp, "bin"), os.path.join(tmp, "out")
            os.mkdir(bindir)
            for tool in ("ffmpeg", "ffprobe"):
                os.symlink(shutil.which(tool), os.path.join(bindir, tool))
            p = subprocess.run([sys.executable, "-I", os.path.join(HERE, "video_ref.py"), "https://example.com/v", "--out", out],
                               capture_output=True, text=True, env={"PATH": bindir, "HOME": tmp})
            self.assertEqual(p.returncode, 3, p.stderr)
            self.assertIn("brew install yt-dlp", p.stderr)
            self.assertFalse(os.path.exists(out), "a failed run left %s behind" % out)

FAKE_YTDLP = """#!%s
import json, os, shutil, sys
out = os.path.dirname(sys.argv[sys.argv.index("-o") + 1])
with open(os.environ["FAKE_LOG"], "w") as f:
    f.write(os.getcwd())
shutil.copy(os.environ["FAKE_VIDEO"], os.path.join(out, "source.mp4"))
with open(os.path.join(out, "source.info.json"), "w") as f:
    f.write("{not json" if os.environ.get("FAKE_MODE") == "badjson" else json.dumps({"title": "Fake Title"}))
""" % sys.executable


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg missing")
class FakeDownload(unittest.TestCase):
    """A fake yt-dlp on PATH copies a local clip, so the link path runs offline."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.bin = os.path.join(self.tmp, "bin")
        os.mkdir(self.bin)
        for tool in ("ffmpeg", "ffprobe"):
            os.symlink(shutil.which(tool), os.path.join(self.bin, tool))
        with open(os.path.join(self.bin, "yt-dlp"), "w") as f:
            f.write(FAKE_YTDLP)
        os.chmod(os.path.join(self.bin, "yt-dlp"), 0o755)
        self.video = os.path.join(self.tmp, "clip.mp4")
        three_colour_video(self.video)
        self.log = os.path.join(self.tmp, "cwd.log")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cli(self, *args, cwd=None, mode="ok"):
        env = {"PATH": self.bin, "HOME": self.tmp, "FAKE_LOG": self.log, "FAKE_VIDEO": self.video, "FAKE_MODE": mode}
        return subprocess.run([sys.executable, "-I", os.path.join(HERE, "video_ref.py"), "https://example.com/v?id=1", *args],
                              capture_output=True, text=True, env=env, cwd=cwd or self.tmp)

    def test_downloader_runs_inside_the_output_folder_not_the_callers_project(self):
        proj, out = os.path.join(self.tmp, "proj"), os.path.join(self.tmp, "out")
        os.mkdir(proj)
        with open(os.path.join(proj, "yt-dlp.conf"), "w") as f:
            f.write('--exec "touch pwned"\n')
        p = self.run_cli("--out", out, cwd=proj)
        self.assertEqual(p.returncode, 0, p.stderr)
        with open(self.log) as f:
            self.assertEqual(os.path.realpath(f.read()), os.path.realpath(out), "yt-dlp ran where a repo's yt-dlp.conf applies")

    def test_unexpected_error_leaves_no_incoming_folder(self):
        p = self.run_cli(mode="badjson")
        self.assertNotEqual(p.returncode, 0)
        base = os.path.join(self.tmp, "Movies", "video-refs")
        left = [d for d in os.listdir(base) if d.startswith(".incoming")] if os.path.isdir(base) else []
        self.assertEqual(left, [], "half-done work folder left behind")

    def test_default_folder_is_named_from_the_title_and_never_reused(self):
        first, second = self.run_cli(), self.run_cli()
        self.assertEqual((first.returncode, second.returncode), (0, 0), first.stderr + second.stderr)
        base = os.path.join(self.tmp, "Movies", "video-refs")
        self.assertEqual(sorted(os.listdir(base)), ["fake-title", "fake-title-2"])
        self.assertTrue(os.path.isfile(os.path.join(base, "fake-title-2", "index.json")))

if __name__ == "__main__":
    unittest.main()
