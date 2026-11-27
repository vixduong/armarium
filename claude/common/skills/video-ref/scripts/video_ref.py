#!/usr/bin/env python3
"""video_ref.py SOURCE [options]: turn a video link or file into reference material
(frames per scene, contact sheet, subtitles as text, index.json); --page: a web page instead (screenshots, page.json).
Used by the /video-ref skill.
Self-test: python3 -I test_video_ref.py"""
import argparse, base64, json, os, re, shutil, subprocess, sys, tempfile, time, unicodedata
from urllib.parse import urlparse


def check_source(s):
    """("url", s) for an http(s) URL, ("file", abspath) for an existing file; ValueError otherwise."""
    p = urlparse(s)
    if p.scheme in ("http", "https") and p.netloc:
        return ("url", s)
    drive = os.path.splitdrive(s)[0]  # Windows: urlparse reads "C:\x" as scheme "c"
    if s and not s.startswith("-") and (not p.scheme or drive) and os.path.isfile(s):
        return ("file", os.path.abspath(s))
    raise ValueError("not an http(s) link or an existing file: %r" % s)


def slugify(s):
    """Folder-safe name: ASCII [a-z0-9-], at most 60 chars, never empty."""
    s = unicodedata.normalize("NFKD", s.replace("đ", "d").replace("Đ", "D")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60].strip("-") or "video"


def pick_evenly(items, cap):
    """At most cap items, first and last kept, the rest evenly spaced."""
    n = len(items)
    if n <= cap:
        return list(items)
    if cap <= 1:
        return list(items[:cap])
    return [items[round(i * (n - 1) / (cap - 1))] for i in range(cap)]


def parse_showinfo(stderr):
    """Frame timestamps (s) from ffmpeg's showinfo log."""
    return [float(t) for t in re.findall(r"pts_time:\s*(-?[0-9.]+)", stderr)]


def srt_to_text(srt):
    """Subtitle text only: no cue numbers, times or tags; a line repeated by rolling auto-subs is kept once."""
    out = []
    for line in srt.splitlines():
        line = re.sub(r"<[^>]+>", "", line).strip()
        if not line or line.isdigit() or "-->" in line or line in out[-2:]:
            continue
        out.append(line)
    return "\n".join(out)

VIDEO_EXT = {"mp4", "mkv", "webm", "mov", "m4v"}
IMAGE_EXT = {"jpg", "jpeg", "png", "webp", "gif", "heic", "avif"}
DEFAULT_DIR = "video-refs"  # under the current project; holds its own .gitignore so downloads stay out of git


class Fail(Exception):
    def __init__(self, msg, code):
        super().__init__(msg)
        self.code = code


def run(cmd, cwd=None):
    return subprocess.run(cmd, capture_output=True, text=True, errors="replace", cwd=cwd)


def need(tool):
    if not shutil.which(tool):
        raise Fail("%s not found: brew install %s" % (tool, tool), 3)


def tail(text, n=600):
    return text.strip()[-n:]


def probe(path):
    """Duration and stream facts from ffprobe."""
    p = run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", path])
    if p.returncode:
        raise Fail("ffprobe cannot read %s: %s" % (path, tail(p.stderr)), 4)
    data = json.loads(p.stdout or "{}")
    v = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    num, _, den = (v.get("avg_frame_rate") or "0/1").partition("/")
    return {"duration": float(data.get("format", {}).get("duration") or v.get("duration") or 0),
            "width": v.get("width"), "height": v.get("height"),
            "fps": round(float(num) / float(den or 1), 3) if float(den or 1) else None,
            "vcodec": v.get("codec_name"),
            "audio": any(s.get("codec_type") == "audio" for s in data.get("streams", []))}


def frame_times(video, duration, threshold, cap):
    """Scene-cut times plus t=0; under 6 picks, add 6 evenly spaced times; at most cap, evenly kept."""
    # shortcut: the scene score reads luma only, so a hue-only cut is missed; the even samples cover short clips
    p = run(["ffmpeg", "-hide_banner", "-nostats", "-i", video, "-an",
             "-vf", "select='gt(scene,%s)',showinfo" % threshold, "-f", "null", "-"])
    times = sorted({0.0, *(round(t, 3) for t in parse_showinfo(p.stderr) if t > 0)})
    if len(times) < 6 and duration > 0:
        times = sorted(set(times) | {round(duration * i / 6, 3) for i in range(6)})
    return pick_evenly(times, cap)


def grab(src, dst, t=None):
    cmd = ["ffmpeg", "-v", "error", "-y"] + (["-ss", str(t)] if t is not None else []) + \
          ["-i", src, "-frames:v", "1", "-vf", "scale='min(1024,iw)':-2", "-q:v", "3", dst]
    p = run(cmd)
    if p.returncode or not os.path.isfile(dst):
        raise Fail("ffmpeg could not write %s: %s" % (dst, tail(p.stderr)), 4)


def contact_sheet(out, n):
    """6 columns of 320 px cells, every cell the size of the first frame's aspect, padded."""
    first = probe(os.path.join(out, "frames", "001.jpg"))
    w, h = 320, max(2, round(320 * (first["height"] or 9) / (first["width"] or 16) / 2) * 2)
    rows = (n + 5) // 6
    vf = "scale=%d:%d:force_original_aspect_ratio=decrease,pad=%d:%d:(ow-iw)/2:(oh-ih)/2,tile=6x%d" % (w, h, w, h, rows)
    p = run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(out, "frames", "%03d.jpg"),
             "-vf", vf, "-frames:v", "1", os.path.join(out, "contact.jpg")])
    if p.returncode:
        raise Fail("contact sheet failed: %s" % tail(p.stderr), 4)


def fetch(url, out, images_only, browser):
    """Download into out/: the video with info and subtitles via yt-dlp, else the post's images via gallery-dl."""
    cookies = ["--cookies-from-browser", browser] if browser else []
    errors = []
    if not images_only:
        need("yt-dlp")
        # --ignore-errors: a failed subtitle (YouTube answers 429 on auto-translated tracks) must not stop the video
        p = run(["yt-dlp", *cookies, "--ignore-errors", "--no-playlist", "--restrict-filenames", "--max-filesize", "1G",
                 "-f", "bv*[height<=1080]+ba/b[height<=1080]/b", "--write-info-json",
                 "--write-subs", "--write-auto-subs", "--sub-langs", "vi.*,en.*", "--convert-subs", "srt",
                 "-o", os.path.join(out, "source.%(ext)s"), "--", url], cwd=out)  # cwd: yt-dlp reads ./yt-dlp.conf, which may hold --exec
        if p.returncode:
            errors.append("yt-dlp: " + tail(p.stderr))
    if not files_with(out, VIDEO_EXT):
        need("gallery-dl")
        p = run(["gallery-dl", *cookies, "-D", os.path.join(out, "images"), "--", url], cwd=out)
        if p.returncode:
            errors.append("gallery-dl: " + tail(p.stderr))
    if not files_with(out, VIDEO_EXT) and not files_with(os.path.join(out, "images"), IMAGE_EXT | VIDEO_EXT):
        raise Fail("nothing downloaded from %s\n%s" % (url, "\n".join(errors)), 4)
    info = {}
    if os.path.isfile(os.path.join(out, "source.info.json")):
        with open(os.path.join(out, "source.info.json"), encoding="utf-8") as f:
            info = json.load(f)
    return info


def files_with(d, exts):
    if not os.path.isdir(d):
        return []
    return sorted(os.path.join(d, f) for f in os.listdir(d) if f.rsplit(".", 1)[-1].lower() in exts)


def unique_dir(base, slug):
    path, i = os.path.join(base, slug), 2
    while os.path.exists(path):
        path, i = os.path.join(base, "%s-%d" % (slug, i)), i + 1
    return path


def build(out, args, kind, source, info):
    """Frames, contact sheet, transcripts and index.json inside out/."""
    os.makedirs(os.path.join(out, "frames"), exist_ok=True)
    videos = files_with(out, VIDEO_EXT) + files_with(os.path.join(out, "images"), VIDEO_EXT)
    video = source if kind == "file" else (videos[0] if videos else None)
    meta, frames = {}, []
    if video:
        meta = probe(video)
        for i, t in enumerate(frame_times(video, meta["duration"], args.threshold, args.max_frames), 1):
            grab(video, os.path.join(out, "frames", "%03d.jpg" % i), t)
            frames.append({"file": "frames/%03d.jpg" % i, "t": t})
    else:
        for i, img in enumerate(pick_evenly(files_with(os.path.join(out, "images"), IMAGE_EXT), args.max_frames), 1):
            grab(img, os.path.join(out, "frames", "%03d.jpg" % i))
            frames.append({"file": "frames/%03d.jpg" % i, "source": os.path.relpath(img, out)})
    if not frames:
        raise Fail("no frames could be taken from %s" % source, 4)
    contact_sheet(out, len(frames))
    transcripts = []
    for srt in files_with(out, {"srt"}):
        lang = os.path.basename(srt)[len("source."):-len(".srt")] or "und"
        name = "transcript.%s.txt" % slugify(lang)
        with open(srt, encoding="utf-8", errors="replace") as f, open(os.path.join(out, name), "w", encoding="utf-8") as g:
            g.write(srt_to_text(f.read()) + "\n")
        transcripts.append(name)
    index = {"source": source, "kind": kind, "title": info.get("title"), "uploader": info.get("uploader"),
             "webpage_url": info.get("webpage_url"), "duration": meta.get("duration"), "meta": meta,
             "frames": frames, "contact": "contact.jpg", "transcripts": transcripts,
             "images": len(files_with(os.path.join(out, "images"), IMAGE_EXT))}
    if os.path.isfile(os.path.join(out, "page.json")):
        index["page"] = "page.json"
    with open(os.path.join(out, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    return index


CHROME_PATHS = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Chromium.app/Contents/MacOS/Chromium"]
CHROME_NAMES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"]
VIEWPORT = (1440, 900)
CALL_TIMEOUT, LOAD_TIMEOUT = 30, 45  # seconds: one CDP call, the page's load event
MAX_REQUESTS = 2000  # Network.requestWillBeSent events kept; the rest of Chrome's events (data chunks, console) are dropped as they arrive
ASSET_EXT = {"mp4", "webm", "glb", "gltf", "ktx2", "hdr", "exr", "riv", "lottie", "wasm"}
ASSET_CAP, ANIMATION_CAP, URL_CAP, TITLE_CAP, MAX_HEIGHT = 80, 60, 500, 200, 100000
MAX_BUFFER = 32 << 20  # bytes of one unfinished Chrome message
PAGE_HEIGHT_JS = "document.documentElement.scrollHeight"
PAGE_LIBS = ("three", "gsap", "lottie", "rive", "pixi", "babylon")
PAGE_INFO_JS = """(() => {
  const canvasContext = c => c.getContext('webgl2') ? 'webgl2' : c.getContext('webgl') ? 'webgl' : 'other';
  const libs = {three: window.THREE || window.__THREE__, gsap: window.gsap, lottie: window.lottie || window.bodymovin,
                rive: window.rive, pixi: window.PIXI, babylon: window.BABYLON};
  return {
    title: document.title.slice(0, 200), height: document.documentElement.scrollHeight,
    videos: [...document.querySelectorAll('video')].slice(0, 20).map(v => String(v.currentSrc || v.src).slice(0, 500)),
    canvases: [...document.querySelectorAll('canvas')].slice(0, 20).map(c => ({width: c.width, height: c.height, context: canvasContext(c)})),
    libs: Object.keys(libs).filter(k => libs[k]),
    animations: document.getAnimations().slice(0, 60).map(a => {
      const t = a.effect ? a.effect.getTiming() : {};
      return {name: String(a.animationName || a.transitionProperty || a.constructor.name).slice(0, 100), duration: t.duration, easing: String(t.easing).slice(0, 100),
              iterations: String(t.iterations), target: a.effect && a.effect.target ? a.effect.target.tagName : null};
    })
  };
})()"""


def find_chrome():
    """Path of a Chrome or Chromium binary, or None."""
    return next((p for p in CHROME_PATHS if os.path.isfile(p)), None) or next(filter(None, map(shutil.which, CHROME_NAMES)), None)


def split_messages(buf):
    """(messages, tail): the complete NUL-ended JSON messages in buf, and the partial one after them."""
    *done, rest = buf.split(b"\0")
    return [json.loads(m) for m in done], rest


class Cdp:
    """Chrome over --remote-debugging-pipe, standard library only: commands on fd 3, replies and events on fd 4."""

    def __init__(self, chrome):
        import fcntl  # POSIX only; main refuses --page on Windows before this runs
        cmd_r, self.cmd_w = os.pipe()
        self.out_r, out_w = os.pipe()

        def wire():  # runs in the child: move the pipe ends to fd 3 and 4, away from whatever fd they got
            a, b = fcntl.fcntl(cmd_r, fcntl.F_DUPFD, 10), fcntl.fcntl(out_w, fcntl.F_DUPFD, 10)
            os.dup2(a, 3)
            os.dup2(b, 4)
        self.profile = tempfile.mkdtemp(prefix="vr-chrome-")  # fresh profile: no cookies, removed in close()
        self.n, self.buf, self.ready, self.events = 0, b"", [], []
        try:
            self.proc = subprocess.Popen(
                [chrome, "--headless=new", "--remote-debugging-pipe", "--user-data-dir=" + self.profile,
                 "--window-size=%d,%d" % VIEWPORT, "--hide-scrollbars", "--no-first-run", "--mute-audio",
                 "--enable-webgl", "--use-angle=metal", "about:blank"],
                pass_fds=(3, 4), preexec_fn=wire, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.SubprocessError) as e:
            self.close()
            raise Fail("cannot start Chrome: %s" % e, 3)
        finally:
            os.close(cmd_r)
            os.close(out_w)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        """Stop Chrome, close the pipes, delete the profile."""
        proc = getattr(self, "proc", None)
        if proc:
            proc.terminate()
            try:
                proc.wait(10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        for fd in (self.cmd_w, self.out_r):
            try:
                os.close(fd)
            except OSError:
                pass
        shutil.rmtree(self.profile, ignore_errors=True)

    def read(self, timeout):
        """Next message within timeout seconds, or None."""
        import select
        end = time.monotonic() + timeout
        while not self.ready:
            left = end - time.monotonic()
            if left <= 0 or not select.select([self.out_r], [], [], left)[0]:
                return None
            try:
                chunk = os.read(self.out_r, 1 << 20)
            except OSError:
                chunk = b""
            if not chunk:
                raise Fail("Chrome closed the connection", 4)
            self.ready, self.buf = split_messages(self.buf + chunk)
            if len(self.buf) > MAX_BUFFER:
                raise Fail("Chrome sent a message over %d MiB" % (MAX_BUFFER >> 20), 4)
        return self.ready.pop(0)

    def pump(self, timeout):
        """Read one message. The load event and at most MAX_REQUESTS request URLs (cut) are kept in self.events; the message is returned."""
        m = self.read(timeout)
        if isinstance(m, dict) and "id" not in m:
            if m.get("method") == "Page.loadEventFired":
                self.events.append({"method": "Page.loadEventFired"})
            elif m.get("method") == "Network.requestWillBeSent" and len(self.events) < MAX_REQUESTS:
                url = (m.get("params") or {}).get("request", {}).get("url")
                if isinstance(url, str):
                    self.events.append({"method": m["method"], "params": {"request": {"url": url[:URL_CAP]}}})
        return m

    def call(self, method, params=None, session=None):
        """Send one command and return its result; Fail(.., 4) on a Chrome error or after CALL_TIMEOUT."""
        self.n += 1
        msg = {"id": self.n, "method": method, "params": params or {}}
        if session:
            msg["sessionId"] = session
        try:
            os.write(self.cmd_w, json.dumps(msg).encode() + b"\0")
        except OSError:
            raise Fail("Chrome closed the connection", 4)
        end = time.monotonic() + CALL_TIMEOUT
        while time.monotonic() < end:
            m = self.pump(end - time.monotonic())
            if m and m.get("id") == self.n:
                if "error" in m:
                    raise Fail("Chrome refused %s: %s" % (method, tail(json.dumps(m["error"]), 200)), 4)
                return m["result"]
        raise Fail("Chrome did not answer %s in %d s" % (method, CALL_TIMEOUT), 4)

    def wait_event(self, method, timeout):
        """Block until an event named method has arrived; Fail(.., 4) after timeout seconds."""
        end = time.monotonic() + timeout
        while not any(e.get("method") == method for e in self.events):
            if time.monotonic() >= end:
                raise Fail("no %s from Chrome in %d s" % (method, timeout), 4)
            self.pump(end - time.monotonic())

    def pause(self, seconds):
        """Wait seconds while still collecting events."""
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.pump(end - time.monotonic())


def run_page(chrome, url, out, args):
    """capture_page inside a fresh Chrome; a malformed reply or a dead pipe is Fail(.., 4)."""
    try:
        with Cdp(chrome) as cdp:
            return capture_page(cdp, url, out, args)
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as e:
        raise Fail("Chrome sent something unexpected: %s: %s" % (type(e).__name__, e), 4)


def page_plan(height, strip, scrolls):
    """Shots to take, in order: the rest strip, the pointer pass, then one scroll shot per viewport height."""
    w, h = VIEWPORT
    plan = [{"pass": "rest"} for _ in range(strip)]
    plan += [{"pass": "pointer", "x": int(w * f), "y": h // 2} for f in (0.2, 0.5, 0.8)]
    plan += [{"pass": "scroll", "scroll": min(y, height - h)} for y in range(h, height, h)][:scrolls]  # the browser clamps at the page end
    return plan


def page_height(v):
    """A page height in px: at most MAX_HEIGHT, 0 when v is not a positive int."""
    return min(v, MAX_HEIGHT) if isinstance(v, int) and not isinstance(v, bool) and v > 0 else 0


def http_urls(urls, cap):
    """The http(s) strings of urls, each cut to URL_CAP, at most cap."""
    return [u[:URL_CAP] for u in urls if isinstance(u, str) and u.lower().startswith(("http://", "https://"))][:cap]


def pick_assets(urls):
    """Unique http(s) URLs of motion and 3D assets, at most ASSET_CAP."""
    kept = [u for u in dict.fromkeys(http_urls(urls, len(urls))) if urlparse(u).path.rsplit(".", 1)[-1].lower() in ASSET_EXT]
    return kept[:ASSET_CAP]


def clean_page_info(raw, requests):
    """What the page told us, cut and capped: it is hostile content."""
    def text(v, cap):
        return v[:cap] if isinstance(v, str) else None

    def count(v):
        return v if isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 100000 else 0
    canvases = [{"width": count(c.get("width")), "height": count(c.get("height")), "context": c.get("context") if c.get("context") in ("webgl2", "webgl") else "other"}
                for c in raw.get("canvases", [])[:20] if isinstance(c, dict)]
    animations = [{"name": text(a.get("name"), 100), "duration": a.get("duration") if isinstance(a.get("duration"), (int, float)) else None,
                   "easing": text(a.get("easing"), 100), "iterations": text(a.get("iterations"), 20), "target": text(a.get("target"), 20)}
                  for a in raw.get("animations", [])[:ANIMATION_CAP] if isinstance(a, dict)]
    return {"title": text(raw.get("title"), TITLE_CAP) or "", "height": page_height(raw.get("height")),
            "videos": http_urls(raw.get("videos", []), 20), "canvases": canvases,
            "libs": sorted(set(raw.get("libs", [])) & set(PAGE_LIBS)), "animations": animations, "assets": pick_assets(requests)}


def evaluate(cdp, expression, session, kind):
    """Value of a JS expression, which must be of type kind; Fail(.., 4) when the page's script threw or answered otherwise."""
    reply = cdp.call("Runtime.evaluate", {"expression": expression, "returnByValue": True}, session)
    value = (reply.get("result") or {}).get("value")
    if "exceptionDetails" in reply or not isinstance(value, kind) or isinstance(value, bool):
        raise Fail("the page did not answer the probe", 4)
    return value


def capture_page(cdp, url, out, args):
    """Load url, write out/images/NNN-pass.jpg and out/page.json; returns the cleaned page info."""
    w, h = VIEWPORT
    target = next(t for t in cdp.call("Target.getTargets")["targetInfos"] if t["type"] == "page")
    s = cdp.call("Target.attachToTarget", {"targetId": target["targetId"], "flatten": True})["sessionId"]
    cdp.call("Browser.setDownloadBehavior", {"behavior": "deny"})
    cdp.call("Page.enable", session=s)
    cdp.call("Network.enable", session=s)
    cdp.call("Emulation.setDeviceMetricsOverride", {"width": w, "height": h, "deviceScaleFactor": 1, "mobile": False}, s)
    if cdp.call("Page.navigate", {"url": url}, s).get("errorText"):
        raise Fail("Chrome could not load %s" % url, 4)
    cdp.wait_event("Page.loadEventFired", LOAD_TIMEOUT)
    cdp.pause(args.wait)
    height = page_height(evaluate(cdp, PAGE_HEIGHT_JS, s, int))  # the canvas probe waits until after the shots: getContext can create a context
    os.makedirs(os.path.join(out, "images"), exist_ok=True)
    shots, first = [], None
    for i, shot in enumerate(page_plan(height, args.strip, args.scrolls), 1):
        if shot["pass"] == "rest":
            cdp.pause(0.25 if i > 1 else 0)
        elif shot["pass"] == "pointer":
            cdp.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": shot["x"], "y": shot["y"]}, s)
            cdp.pause(0.3)
        else:
            cdp.call("Runtime.evaluate", {"expression": "window.scrollTo(0, %d)" % shot["scroll"]}, s)
            cdp.pause(0.5)
        name = "images/%03d-%s.jpg" % (i, shot["pass"])
        with open(os.path.join(out, name), "wb") as f:
            f.write(base64.b64decode(cdp.call("Page.captureScreenshot", {"format": "jpeg", "quality": 85}, s)["data"]))
        taken = time.monotonic()
        first = taken if first is None else first
        shots.append({"file": name, **shot, "t": round(taken - first, 2)})
    raw = evaluate(cdp, PAGE_INFO_JS, s, dict)
    requests = [e["params"]["request"]["url"] for e in cdp.events if e.get("method") == "Network.requestWillBeSent"]
    page = {"url": url, "viewport": {"width": w, "height": h}, **clean_page_info(raw, requests), "shots": shots}
    with open(os.path.join(out, "page.json"), "w", encoding="utf-8") as f:
        json.dump(page, f, ensure_ascii=False, indent=1)
    return page


def main(argv):
    ap = argparse.ArgumentParser(prog="video_ref.py", description=__doc__.splitlines()[0])
    ap.add_argument("source", help="http(s) link or local video file")
    ap.add_argument("--name", help="folder name (default: title or file name)")
    ap.add_argument("--dir", help="parent folder (default: ./%s in the current project)" % DEFAULT_DIR)
    ap.add_argument("--out", help="exact output folder (overrides --dir and --name)")
    ap.add_argument("--max-frames", type=int, default=40)
    ap.add_argument("--threshold", type=float, default=0.3, help="scene-change score, 0..1")
    ap.add_argument("--images", action="store_true", help="link is an image post: use gallery-dl only")
    ap.add_argument("--browser", help="read login cookies from this browser (chrome, safari, firefox...)")
    ap.add_argument("--page", action="store_true", help="link is a web page: headless Chrome screenshots (rest strip, pointer, scroll) and page.json")
    ap.add_argument("--strip", type=int, default=8, help="--page: frames in the rest strip, 0.25 s apart (1..30)")
    ap.add_argument("--scrolls", type=int, default=6, help="--page: most scroll shots, one per viewport height (0..20)")
    ap.add_argument("--wait", type=float, default=3, help="--page: seconds to let the page settle after load (0..30)")
    args = ap.parse_args(argv)
    work, created, emptied, done = None, False, False, False
    try:
        try:
            kind, source = check_source(args.source)
        except ValueError as e:
            raise Fail(str(e), 2)
        if args.max_frames < 1 or not 0 < args.threshold < 1:
            raise Fail("--max-frames must be >= 1 and --threshold between 0 and 1", 2)
        if args.page:
            if kind != "url" or args.images:
                raise Fail("--page needs an http(s) link and cannot be combined with --images", 2)
            if not (1 <= args.strip <= 30 and 0 <= args.scrolls <= 20 and 0 <= args.wait <= 30):
                raise Fail("--strip must be 1..30, --scrolls 0..20, --wait 0..30", 2)
            if os.name == "nt":
                raise Fail("--page needs macOS or Linux", 3)
            chrome = find_chrome()
            if not chrome:
                raise Fail("Chrome not found: install Google Chrome or Chromium", 3)
        if args.out and os.path.exists(args.out) and not os.path.isdir(args.out):
            raise Fail("--out %s is not a folder" % args.out, 2)
        if args.out and os.path.exists(args.out) and os.listdir(args.out):
            raise Fail("--out %s is not empty" % args.out, 2)
        for tool in ["ffmpeg", "ffprobe"] + ([("gallery-dl" if args.images else "yt-dlp")] if kind == "url" and not args.page else []):
            need(tool)
        if args.out:
            work = os.path.abspath(args.out)
            created = not os.path.exists(work)
            emptied = not created  # it exists and was checked empty: what a failed run leaves in it is ours to remove
            os.makedirs(work, exist_ok=True)
        else:
            base = os.path.abspath(args.dir or DEFAULT_DIR)
            if not os.path.exists(base):
                os.makedirs(base)
                with open(os.path.join(base, ".gitignore"), "w") as f:
                    f.write("*\n")
            work, created = tempfile.mkdtemp(prefix=".incoming-", dir=base), True
        if args.page:
            info = {"title": run_page(chrome, source, work, args)["title"]}
        else:
            info = fetch(source, work, args.images, args.browser) if kind == "url" else {}
        if not args.out:
            stem = args.name or info.get("title") or os.path.splitext(os.path.basename(source))[0]
            final = unique_dir(base, slugify(stem))
            os.rename(work, final)
            work = final
        index = build(work, args, kind, source, info)
        done = True
    except Fail as e:
        print("video_ref: " + str(e), file=sys.stderr)
        return e.code
    finally:
        if created and not done:  # only a folder this run made; a half-filled one would look like a finished reference
            shutil.rmtree(work, ignore_errors=True)
        elif emptied and not done:  # the caller's own empty folder: keep it, empty it again
            for name in os.listdir(work):
                p = os.path.join(work, name)
                shutil.rmtree(p, ignore_errors=True) if os.path.isdir(p) and not os.path.islink(p) else os.remove(p)
    print(work)
    print("%d frames, %d transcript(s), %d image(s); open contact.jpg first" % (len(index["frames"]), len(index["transcripts"]), index["images"]))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
