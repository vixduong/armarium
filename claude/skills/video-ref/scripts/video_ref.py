#!/usr/bin/env python3
"""video_ref.py SOURCE [options]: turn a video link or file into reference material
(frames per scene, contact sheet, subtitles as text, index.json). Used by the /video-ref skill.
Self-test: python3 -I test_video_ref.py"""
import argparse, json, os, re, shutil, subprocess, sys, unicodedata
from urllib.parse import urlparse


def check_source(s):
    """("url", s) for an http(s) URL, ("file", abspath) for an existing file; ValueError otherwise."""
    p = urlparse(s)
    if p.scheme in ("http", "https") and p.netloc:
        return ("url", s)
    if s and not s.startswith("-") and not p.scheme and os.path.isfile(s):
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
DEFAULT_BASE = os.path.expanduser("~/Movies/video-refs")


class Fail(Exception):
    def __init__(self, msg, code):
        super().__init__(msg)
        self.code = code


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, errors="replace")


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
                 "-o", os.path.join(out, "source.%(ext)s"), "--", url])
        if p.returncode:
            errors.append("yt-dlp: " + tail(p.stderr))
    if not files_with(out, VIDEO_EXT):
        need("gallery-dl")
        p = run(["gallery-dl", *cookies, "-D", os.path.join(out, "images"), "--", url])
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
    with open(os.path.join(out, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    return index


def main(argv):
    ap = argparse.ArgumentParser(prog="video_ref.py", description=__doc__.splitlines()[0])
    ap.add_argument("source", help="http(s) link or local video file")
    ap.add_argument("--name", help="folder name (default: title or file name)")
    ap.add_argument("--out", help="exact output folder (default: %s/<name>)" % DEFAULT_BASE)
    ap.add_argument("--max-frames", type=int, default=40)
    ap.add_argument("--threshold", type=float, default=0.3, help="scene-change score, 0..1")
    ap.add_argument("--images", action="store_true", help="link is an image post: use gallery-dl only")
    ap.add_argument("--browser", help="read login cookies from this browser (chrome, safari, firefox...)")
    args = ap.parse_args(argv)
    work, created = None, False
    try:
        try:
            kind, source = check_source(args.source)
        except ValueError as e:
            raise Fail(str(e), 2)
        if args.max_frames < 1 or not 0 < args.threshold < 1:
            raise Fail("--max-frames must be >= 1 and --threshold between 0 and 1", 2)
        if args.out and os.path.exists(args.out) and os.listdir(args.out):
            raise Fail("--out %s is not empty" % args.out, 2)
        for tool in ["ffmpeg", "ffprobe"] + ([("gallery-dl" if args.images else "yt-dlp")] if kind == "url" else []):
            need(tool)
        base = os.path.dirname(os.path.abspath(args.out)) if args.out else DEFAULT_BASE
        work = os.path.abspath(args.out) if args.out else os.path.join(base, ".incoming-%d" % os.getpid())
        created = not os.path.exists(work)
        os.makedirs(work, exist_ok=True)
        info = fetch(source, work, args.images, args.browser) if kind == "url" else {}
        if not args.out:
            stem = args.name or info.get("title") or os.path.splitext(os.path.basename(source))[0]
            final = unique_dir(base, slugify(stem))
            os.rename(work, final)
            work = final
        index = build(work, args, kind, source, info)
    except Fail as e:
        if created:  # only a folder this run made; a half-filled one would look like a finished reference
            shutil.rmtree(work, ignore_errors=True)
        print("video_ref: " + str(e), file=sys.stderr)
        return e.code
    print(work)
    print("%d frames, %d transcript(s), %d image(s); open contact.jpg first" % (len(index["frames"]), len(index["transcripts"]), index["images"]))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
