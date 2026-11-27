"""Self-test for video_ref.py: python3 -I test_video_ref.py (run by armarium bin/check)."""
import argparse, base64, contextlib, importlib.util, io, json, os, shutil, subprocess, sys, tempfile, unittest, unittest.mock

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
@unittest.skipIf(sys.platform == "win32", "fake tool bin: symlinks and extensionless scripts need POSIX")
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
@unittest.skipIf(sys.platform == "win32", "fake tool bin: symlinks and extensionless scripts need POSIX")
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

    def test_out_that_is_a_file_exits_2_with_a_message(self):
        out = os.path.join(self.tmp, "taken.txt")
        with open(out, "w") as f:
            f.write("x")
        p = self.run_cli("--out", out)
        self.assertEqual(p.returncode, 2, p.stderr)
        self.assertIn("not a folder", p.stderr)
        self.assertNotIn("Traceback", p.stderr)

    def test_failed_run_leaves_an_empty_out_folder_empty(self):
        out = os.path.join(self.tmp, "out")
        os.mkdir(out)
        p = self.run_cli("--out", out, mode="badjson")
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(os.listdir(out), [], "a half-filled folder would look like a finished reference")

    def test_unexpected_error_leaves_no_incoming_folder(self):
        p = self.run_cli(mode="badjson")
        self.assertNotEqual(p.returncode, 0)
        base = os.path.join(self.tmp, "video-refs")
        left = [d for d in os.listdir(base) if d.startswith(".incoming")] if os.path.isdir(base) else []
        self.assertEqual(left, [], "half-done work folder left behind")

    def test_default_folder_is_video_refs_in_the_current_project_named_from_the_title(self):
        proj = os.path.join(self.tmp, "proj")
        os.mkdir(proj)
        first, second = self.run_cli(cwd=proj), self.run_cli(cwd=proj)
        self.assertEqual((first.returncode, second.returncode), (0, 0), first.stderr + second.stderr)
        base = os.path.join(proj, "video-refs")
        self.assertTrue(os.path.isdir(base), "no video-refs/ in the project")
        self.assertEqual(sorted(os.listdir(base)), [".gitignore", "fake-title", "fake-title-2"])
        self.assertTrue(os.path.isfile(os.path.join(base, "fake-title-2", "index.json")))
        with open(os.path.join(base, ".gitignore")) as f:
            self.assertEqual(f.read(), "*\n", "downloads must stay out of the project's git")

    def test_dir_sets_the_parent_folder(self):
        refs = os.path.join(self.tmp, "my", "refs")
        p = self.run_cli("--dir", refs)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(os.path.isfile(os.path.join(refs, "fake-title", "index.json")))


class FakeCdp:
    """Stands in for Chrome: answers the calls capture_page makes and records them."""

    def __init__(self, info, requests, shot=b"jpeg"):
        self.info, self.shot, self.calls, self.pauses = info, shot, [], []
        self.events = [{"method": "Network.requestWillBeSent", "params": {"request": {"url": u}}} for u in requests]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def call(self, method, params=None, session=None):
        self.calls.append((method, params))
        if method == "Target.getTargets":
            return {"targetInfos": [{"type": "page", "targetId": "T"}]}
        if method == "Target.attachToTarget":
            return {"sessionId": "S"}
        if method == "Runtime.evaluate" and params["expression"] == vr.PAGE_HEIGHT_JS:
            return {"result": {"value": self.info["height"]}}
        if method == "Runtime.evaluate" and params["expression"] == vr.PAGE_INFO_JS:
            return {"result": {"value": self.info}}
        if method == "Page.captureScreenshot":
            return {"data": base64.b64encode(self.shot).decode()}
        return {}

    def wait_event(self, method, timeout):
        self.calls.append(("wait_event", method))

    def pause(self, seconds):
        self.pauses.append(seconds)


class SplitMessages(unittest.TestCase):
    def test_two_messages_and_a_partial_tail(self):
        msgs, rest = vr.split_messages(b'{"id": 1}\0{"id": 2, "r": "\xc3\xa9"}\0{"id": 3')
        self.assertEqual(msgs, [{"id": 1}, {"id": 2, "r": "\xe9"}])
        self.assertEqual(rest, b'{"id": 3')


class PagePlan(unittest.TestCase):
    def of(self, plan, name):
        return [s for s in plan if s["pass"] == name]

    def test_strip_then_three_pointer_shots(self):
        plan = vr.page_plan(3000, 4, 6)
        self.assertEqual([s["pass"] for s in plan[:4]], ["rest"] * 4)
        self.assertEqual(len(self.of(plan, "pointer")), 3)

    def test_scroll_offsets_stop_at_the_page_end_and_at_the_cap(self):
        self.assertEqual([s["scroll"] for s in self.of(vr.page_plan(2000, 1, 6), "scroll")], [900, 1100])
        self.assertEqual(len(self.of(vr.page_plan(100000, 1, 6), "scroll")), 6)

    def test_one_viewport_page_has_no_scroll_shots(self):
        self.assertEqual(self.of(vr.page_plan(900, 8, 6), "scroll"), [])


class PickAssets(unittest.TestCase):
    def test_keeps_listed_extensions_with_a_query_string(self):
        urls = ["https://a.io/s.webm?v=2", "https://a.io/m.GLB", "https://a.io/app.js", "https://a.io/p.png"]
        self.assertEqual(vr.pick_assets(urls), ["https://a.io/s.webm?v=2", "https://a.io/m.GLB"])

    def test_drops_non_http_and_duplicates(self):
        urls = ["data:video/mp4;base64,AA", "blob:https://a.io/x.mp4", "ftp://a.io/x.mp4", "https://a.io/x.mp4", "https://a.io/x.mp4"]
        self.assertEqual(vr.pick_assets(urls), ["https://a.io/x.mp4"])

    def test_capped_at_80(self):
        self.assertEqual(len(vr.pick_assets(["https://a.io/%d.mp4" % i for i in range(200)])), 80)


class CleanPageInfo(unittest.TestCase):
    RAW = {"title": "T" * 300, "height": 1800, "libs": ["three", "evil"], "videos": ["blob:https://a.io/1", "https://a.io/v.webm"],
           "canvases": [{"width": 1440, "height": 900, "context": "webgl2"}],
           "animations": [{"name": "spin", "duration": 1000, "easing": "linear", "iterations": "Infinity", "target": "DIV"}] * 100}

    def test_long_title_is_cut_and_script_urls_are_dropped(self):
        page = vr.clean_page_info(dict(self.RAW, videos=["javascript:alert(1)", "data:video/mp4;base64,AA", "blob:x", "https://a.io/v.webm/" + "x" * 600]), [])
        self.assertEqual(len(page["title"]), 200)
        self.assertEqual([len(u) for u in page["videos"]], [500])
        self.assertTrue(page["videos"][0].startswith("https://a.io/v.webm/"))

    def test_animation_list_is_capped_and_unknown_libs_are_dropped(self):
        page = vr.clean_page_info(self.RAW, ["https://a.io/m.glb"])
        self.assertEqual(len(page["animations"]), 60)
        self.assertEqual(page["libs"], ["three"])
        self.assertEqual(page["assets"], ["https://a.io/m.glb"])
        self.assertEqual(page["canvases"], [{"width": 1440, "height": 900, "context": "webgl2"}])

    def test_page_taller_than_the_cap_counts_as_the_cap_not_zero(self):
        self.assertEqual(vr.clean_page_info(dict(self.RAW, height=500000), [])["height"], 100000)


class CapturePage(unittest.TestCase):
    def test_writes_shots_in_plan_order_and_page_json_with_cleaned_fields(self):
        info = dict(CleanPageInfo.RAW, animations=[])
        fake = FakeCdp(info, ["https://a.io/m.glb", "https://a.io/app.js"])
        with tempfile.TemporaryDirectory() as out:
            page = vr.capture_page(fake, "https://example.com/p", out, argparse.Namespace(strip=2, scrolls=6, wait=0))
            names = sorted(os.listdir(os.path.join(out, "images")))
            self.assertEqual(names, ["001-rest.jpg", "002-rest.jpg", "003-pointer.jpg", "004-pointer.jpg", "005-pointer.jpg", "006-scroll.jpg"])
            with open(os.path.join(out, "images", names[0]), "rb") as f:
                self.assertEqual(f.read(), b"jpeg")
            with open(os.path.join(out, "page.json"), encoding="utf-8") as f:
                saved = json.load(f)
        self.assertEqual(saved, page)
        self.assertEqual((saved["url"], len(saved["title"]), saved["height"]), ("https://example.com/p", 200, 1800))
        self.assertEqual(saved["assets"], ["https://a.io/m.glb"])
        self.assertEqual([s["file"] for s in saved["shots"]], ["images/" + n for n in names])
        self.assertIn(("Browser.setDownloadBehavior", {"behavior": "deny"}), fake.calls)

    def capture(self, fake, **kw):
        args = argparse.Namespace(**{"strip": 2, "scrolls": 6, "wait": 0, **kw})
        with tempfile.TemporaryDirectory() as out:
            return vr.capture_page(fake, "https://example.com/p", out, args)

    def test_downloads_are_denied_before_navigation_and_the_load_is_awaited_before_the_first_shot(self):
        fake = FakeCdp(dict(CleanPageInfo.RAW, animations=[]), [])
        self.capture(fake)
        order = [c[0] for c in fake.calls]
        self.assertLess(order.index("Browser.setDownloadBehavior"), order.index("Page.navigate"))
        self.assertLess(order.index("Page.navigate"), order.index("wait_event"))
        self.assertEqual(fake.calls[order.index("wait_event")], ("wait_event", "Page.loadEventFired"))
        self.assertLess(order.index("wait_event"), order.index("Page.captureScreenshot"))

    def test_the_canvas_probe_runs_after_the_last_shot_and_only_the_height_before_the_first(self):
        fake = FakeCdp(dict(CleanPageInfo.RAW, animations=[]), [])
        self.capture(fake)
        evaluated = [(i, c[1]["expression"]) for i, c in enumerate(fake.calls) if c[0] == "Runtime.evaluate"]
        shots = [i for i, c in enumerate(fake.calls) if c[0] == "Page.captureScreenshot"]
        self.assertEqual([i < shots[0] for i, e in evaluated if e == vr.PAGE_HEIGHT_JS], [True])
        self.assertTrue(all(i > shots[-1] for i, e in evaluated if e == vr.PAGE_INFO_JS), "the probe ran before a shot")
        self.assertEqual([e for i, e in evaluated if e == vr.PAGE_INFO_JS], [vr.PAGE_INFO_JS])

    def test_page_taller_than_100000_px_still_gets_its_scroll_shots(self):
        page = self.capture(FakeCdp(dict(CleanPageInfo.RAW, height=500000, animations=[]), []), strip=1, scrolls=2)
        self.assertEqual([s["pass"] for s in page["shots"]].count("scroll"), 2)
        self.assertEqual(page["height"], 100000)

    def test_a_shot_time_is_when_it_was_taken(self):
        ticks = iter(100 + 0.7 * i for i in range(50))
        with unittest.mock.patch.object(vr.time, "monotonic", side_effect=lambda: next(ticks)):
            page = self.capture(FakeCdp(dict(CleanPageInfo.RAW, animations=[]), []), scrolls=0)
        self.assertEqual([s.get("t") for s in page["shots"]], [0, 0.7, 1.4, 2.1, 2.8])

    def test_rest_shots_are_a_quarter_second_apart(self):
        fake = FakeCdp(dict(CleanPageInfo.RAW, animations=[]), [])
        self.capture(fake, strip=4)
        self.assertEqual(fake.pauses.count(0.25), 3)

    def test_a_probe_that_throws_or_answers_the_wrong_type_is_fail_4(self):
        class Probe(FakeCdp):
            def call(self, method, params=None, session=None):
                if method == "Runtime.evaluate" and params["expression"] == vr.PAGE_INFO_JS:
                    return self.reply
                return super().call(method, params, session)
        for reply in ({"exceptionDetails": {"text": "boom"}, "result": {"type": "object"}}, {"result": {"type": "undefined"}}, {"result": {"value": "text"}}):
            fake = Probe(dict(CleanPageInfo.RAW, animations=[]), [])
            fake.reply = reply
            with self.subTest(reply=reply):
                fail_with_code_4(self, self.capture, fake)


def fail_with_code_4(test, fn, *args):
    """Call fn(*args), which must raise Fail with code 4 and nothing else."""
    try:
        fn(*args)
    except vr.Fail as e:
        test.assertEqual(e.code, 4)
        return e
    except Exception as e:
        test.fail("%s leaked %r instead of Fail" % (getattr(fn, "__name__", fn), e))
    test.fail("%s did not fail" % getattr(fn, "__name__", fn))


class CdpPipe(unittest.TestCase):
    """A Cdp wired to plain pipes instead of Chrome: the test writes what Chrome would say to self.feed."""

    def setUp(self):
        self.cdp = vr.Cdp.__new__(vr.Cdp)
        self.cmd_r, self.cdp.cmd_w = os.pipe()
        self.cdp.out_r, self.feed = os.pipe()
        self.cdp.n, self.cdp.buf, self.cdp.ready, self.cdp.events = 0, b"", [], []
        self.addCleanup(self.close_all)

    def close_all(self):
        for fd in (self.cmd_r, self.cdp.cmd_w, self.cdp.out_r, self.feed):
            try:
                os.close(fd)
            except OSError:
                pass

    def test_a_message_split_across_two_chunks_is_returned_whole_after_the_second(self):
        os.write(self.feed, b'{"id": 1, "res')
        self.assertIsNone(self.cdp.read(0.1))
        os.write(self.feed, b'ult": {}}\0')
        self.assertEqual(self.cdp.read(1), {"id": 1, "result": {}})

    def test_end_of_file_is_fail_4(self):
        os.close(self.feed)
        fail_with_code_4(self, self.cdp.read, 1)

    def test_a_reply_that_never_comes_is_fail_4(self):
        with unittest.mock.patch.object(vr, "CALL_TIMEOUT", 0.2):
            self.assertIn("did not answer", str(fail_with_code_4(self, self.cdp.call, "Page.enable")))

    def test_an_error_reply_is_fail_4(self):
        os.write(self.feed, b'{"id": 1, "error": {"message": "nope"}}\0')
        self.assertIn("refused", str(fail_with_code_4(self, self.cdp.call, "Page.enable")))

    def test_a_dead_command_pipe_is_fail_4(self):
        os.close(self.cmd_r)
        fail_with_code_4(self, self.cdp.call, "Page.enable")

    def test_a_reply_buffer_past_the_cap_is_fail_4(self):
        self.cdp.buf = b"x" * vr.MAX_BUFFER
        os.write(self.feed, b"y")
        fail_with_code_4(self, self.cdp.read, 1)

    def test_requests_are_kept_as_a_url_cut_to_500_chars_at_most_2000_and_the_load_event_always(self):
        request = {"method": "Network.requestWillBeSent", "params": {"request": {"url": "https://a.io/" + "x" * 900, "postData": "secret"}}}
        self.cdp.read = lambda timeout: request
        for _ in range(2100):
            self.cdp.pump(0)
        self.cdp.read = lambda timeout: {"method": "Page.loadEventFired", "params": {}}
        self.cdp.pump(0)
        self.assertEqual(len(self.cdp.events), 2001)
        self.assertEqual({len(e["params"]["request"]["url"]) for e in self.cdp.events[:-1]}, {500})
        self.assertNotIn("secret", json.dumps(self.cdp.events))
        self.assertEqual(self.cdp.events[-1]["method"], "Page.loadEventFired")


class CdpStart(unittest.TestCase):
    def start(self, error):
        """Cdp("/no/chrome") with Popen raising error: (what it raised, Popen mock, fds and profile folders it made)."""
        made = {"fds": [], "dirs": []}
        real_pipe, real_mkdtemp = os.pipe, tempfile.mkdtemp

        def pipe():
            fds = real_pipe()
            made["fds"].extend(fds)
            return fds

        def mkdtemp(**kw):
            made["dirs"].append(real_mkdtemp(**kw))
            return made["dirs"][-1]
        with unittest.mock.patch.object(os, "pipe", pipe), unittest.mock.patch.object(tempfile, "mkdtemp", mkdtemp), \
                unittest.mock.patch.object(subprocess, "Popen", side_effect=error) as popen:
            try:
                vr.Cdp("/no/chrome")
            except vr.Fail as e:
                return e, popen, made
            except Exception as e:
                for fd in made["fds"]:
                    try:
                        os.close(fd)
                    except OSError:
                        pass
                for d in made["dirs"]:
                    shutil.rmtree(d, ignore_errors=True)
                self.fail("Cdp leaked %r instead of Fail" % e)
        self.fail("Cdp started")

    def test_a_failed_start_is_fail_3_and_removes_the_profile_and_closes_both_pipes(self):
        for error in (OSError("no such file"), subprocess.SubprocessError("Exception occurred in preexec_fn.")):
            with self.subTest(error=error):
                e, _, made = self.start(error)
                self.assertEqual(e.code, 3)
                self.assertEqual([os.path.exists(d) for d in made["dirs"]], [False])
                for fd in made["fds"]:
                    with self.assertRaises(OSError):
                        os.fstat(fd)

    def test_chrome_runs_without_ignore_gpu_blocklist(self):
        _, popen, _ = self.start(OSError("x"))
        self.assertNotIn("--ignore-gpu-blocklist", popen.call_args[0][0])


class RunPage(unittest.TestCase):
    def test_a_malformed_reply_or_a_dead_pipe_is_fail_4(self):
        for error in (KeyError("result"), OSError("broken pipe"), TypeError("x"), ValueError("bad json"), StopIteration()):
            with self.subTest(error=error), unittest.mock.patch.object(vr, "Cdp"), unittest.mock.patch.object(vr, "capture_page", side_effect=error):
                fail_with_code_4(self, vr.run_page, "/bin/chrome", "https://example.com/", "/nowhere", None)


class PageMode(unittest.TestCase):
    def run_main(self, *argv):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            return vr.main(list(argv)), err.getvalue()

    def test_local_file_with_page_exits_2_and_leaves_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            clip, out = os.path.join(tmp, "clip.mp4"), os.path.join(tmp, "out")
            with open(clip, "wb") as f:
                f.write(b"x")
            code, err = self.run_main(clip, "--page", "--out", out)
            self.assertEqual(code, 2, err)
            self.assertFalse(os.path.exists(out))

    def test_page_with_images_exits_2(self):
        code, err = self.run_main("https://example.com/", "--page", "--images")
        self.assertEqual(code, 2, err)

    def test_out_of_range_strip_scrolls_and_wait_exit_2(self):
        for flag, value in (("--strip", "0"), ("--strip", "31"), ("--scrolls", "-1"), ("--scrolls", "21"), ("--wait", "-1"), ("--wait", "31")):
            with self.subTest(flag=flag, value=value):
                code, err = self.run_main("https://example.com/", "--page", flag, value)
                self.assertEqual(code, 2, err)

    def test_no_chrome_exits_3_and_leaves_nothing(self):
        with tempfile.TemporaryDirectory() as tmp, unittest.mock.patch.object(vr, "find_chrome", return_value=None):
            out = os.path.join(tmp, "out")
            code, err = self.run_main("https://example.com/", "--page", "--out", out)
            self.assertEqual(code, 3, err)
            self.assertFalse(os.path.exists(out))


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg missing")
class PageBuild(PageMode):
    def test_a_failed_capture_exits_4_and_leaves_no_folder(self):
        with tempfile.TemporaryDirectory() as tmp, unittest.mock.patch.object(vr, "find_chrome", return_value="/bin/chrome"), \
                unittest.mock.patch.object(vr, "Cdp"), unittest.mock.patch.object(vr, "capture_page", side_effect=vr.Fail("no load", 4)):
            out = os.path.join(tmp, "out")
            code, err = self.run_main("https://example.com/", "--page", "--out", out)
            self.assertEqual((code, os.path.exists(out)), (4, False), err)

    def test_a_page_run_writes_frames_and_index_json_names_page_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            jpeg, out = os.path.join(tmp, "red.jpg"), os.path.join(tmp, "out")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=red:s=64x36", "-frames:v", "1", jpeg], check=True)
            with open(jpeg, "rb") as f:
                fake = FakeCdp(dict(CleanPageInfo.RAW, animations=[]), [], shot=f.read())
            with unittest.mock.patch.object(vr, "find_chrome", return_value="/bin/chrome"), unittest.mock.patch.object(vr, "Cdp", return_value=fake):
                code, err = self.run_main("https://example.com/p", "--page", "--out", out, "--strip", "1", "--scrolls", "0", "--wait", "0")
            self.assertEqual(code, 0, err)
            with open(os.path.join(out, "index.json"), encoding="utf-8") as f:
                index = json.load(f)
            self.assertEqual((index["page"], len(index["frames"])), ("page.json", 4))
            self.assertTrue(os.path.isfile(os.path.join(out, "contact.jpg")))


if __name__ == "__main__":
    unittest.main()
