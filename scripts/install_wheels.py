"""Resolve wheel dependencies, record their hashes, and install with pip's hash checks."""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
from zipfile import ZipFile


def install(wheelhouse):
    wheels = sorted(wheelhouse.glob("*.whl"))
    assert len(wheels) == 2, "Expected the launcher and one PG16 binary wheel"
    for wheel in wheels:
        with ZipFile(wheel) as archive:
            metadata = archive.read(next(n for n in archive.namelist() if n.endswith(".dist-info/WHEEL"))).decode()
            if wheel.name.startswith("pgserver_postgres_"):
                assert "Root-Is-Purelib: false" in metadata
                assert "Tag: py3-none-" in metadata and "Tag: py3-none-any" not in metadata
                assert any(n.endswith("/bin/postgres") for n in archive.namelist())
            else:
                assert "Tag: py3-none-any" in metadata
                assert all("pginstall/" not in n for n in archive.namelist())
    dependencies = Path(tempfile.mkdtemp(prefix="dependencies-", dir=wheelhouse))
    subprocess.run([sys.executable, "-m", "pip", "download", "--only-binary=:all:",
                    "--dest", str(dependencies), *map(str, wheels)], check=True)
    requirements = wheelhouse / "requirements-local.txt"
    requirements.write_text("".join(
        f"{p.resolve().as_uri()} --hash=sha256:{hashlib.sha256(p.read_bytes()).hexdigest()}\n"
        for p in sorted(dependencies.glob("*.whl"))))
    subprocess.run([sys.executable, "-m", "pip", "install", "--no-index", "--require-hashes",
                    "--force-reinstall", "-r", str(requirements)], check=True)


if __name__ == "__main__":
    install(Path(sys.argv[1]))
