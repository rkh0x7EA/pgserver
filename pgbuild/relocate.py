"""Make every bundled native executable/library independent of the build prefix."""
import os
from pathlib import Path
import subprocess
import sys


def run(*args):
    return subprocess.check_output(args, text=True)


def relocate(prefix):
    for path in sorted(prefix.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        with path.open("rb") as stream:
            magic = stream.read(4)
        if sys.platform == "darwin" and magic in (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf"):
            if path.suffix == ".dylib":
                run("install_name_tool", "-id", "@rpath/" + path.name, str(path))
            for line in run("otool", "-L", str(path)).splitlines()[1:]:
                dependency = line.strip().split(" (", 1)[0]
                if dependency.startswith(str(prefix) + "/"):
                    relative = os.path.relpath(dependency, path.parent)
                    run("install_name_tool", "-change", dependency, "@loader_path/" + relative, str(path))
                elif dependency.startswith("/") and not dependency.startswith(("/usr/lib/", "/System/Library/")):
                    raise RuntimeError(f"Unbundled dependency: {path}: {dependency}")
            run("codesign", "--force", "--sign", "-", str(path))
        elif sys.platform.startswith("linux") and magic == b"\x7fELF":
            relative = os.path.relpath(prefix / "lib", path.parent)
            run("patchelf", "--set-rpath", "$ORIGIN/" + relative, str(path))


if __name__ == "__main__":
    relocate(Path(sys.argv[1]).resolve())
