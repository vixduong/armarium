"""which(name): the program's full path from the absolute PATH entries only. Windows starts a bare name from the cwd
(the user's project) before PATH, and shutil.which searches the cwd there too, so a hook starts programs by full path.
Raises FileNotFoundError, an OSError like the one subprocess gives for a missing program."""
import os


def which(name):
    exts = [e for e in os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";") if e] if os.name == "nt" else [""]
    for d in os.environ.get("PATH", "").split(os.pathsep):
        d = d.strip('"')  # Windows PATH entries may be quoted
        if d and os.path.isabs(d):
            for e in exts:
                p = os.path.join(d, name + e)
                if os.path.isfile(p) and (os.name == "nt" or os.access(p, os.X_OK)):
                    return p
    raise FileNotFoundError(name)
