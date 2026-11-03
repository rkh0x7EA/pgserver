import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def relocator():
    spec = importlib.util.spec_from_file_location("relocate", Path(__file__).parents[1] / "pgbuild/relocate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_elf_rpaths_cover_binaries_and_libraries(tmp_path, monkeypatch, relocator):
    for name in ("bin/postgres", "lib/libpq.so", "lib/postgresql/vector.so"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\x7fELF")
    calls = []
    monkeypatch.setattr(relocator.sys, "platform", "linux")
    monkeypatch.setattr(relocator, "run", lambda *args: calls.append(args))
    relocator.relocate(tmp_path)
    assert len(calls) == 3
    assert {args[2] for args in calls} == {"$ORIGIN/../lib", "$ORIGIN/.", "$ORIGIN/.."}


def test_macho_install_names_and_signatures(tmp_path, monkeypatch, relocator):
    binary = tmp_path / "bin/psql"
    binary.parent.mkdir()
    binary.write_bytes(b"\xcf\xfa\xed\xfe")
    calls = []
    def run(*args):
        calls.append(args)
        return f"{binary}:\n\t{tmp_path}/lib/libpq.5.dylib (compatibility version 5.0.0)\n" if args[0] == "otool" else ""
    monkeypatch.setattr(relocator.sys, "platform", "darwin")
    monkeypatch.setattr(relocator, "run", run)
    relocator.relocate(tmp_path)
    assert ("install_name_tool", "-change", str(tmp_path / "lib/libpq.5.dylib"), "@loader_path/../lib/libpq.5.dylib", str(binary)) in calls
    assert ("codesign", "--force", "--sign", "-", str(binary)) in calls


def test_unbundled_macho_library_is_an_error(tmp_path, monkeypatch, relocator):
    (tmp_path / "postgres").write_bytes(b"\xcf\xfa\xed\xfe")
    monkeypatch.setattr(relocator.sys, "platform", "darwin")
    monkeypatch.setattr(relocator, "run", lambda *args: "postgres:\n\t/opt/homebrew/lib/libbad.dylib (version 1)\n")
    with pytest.raises(RuntimeError, match="Unbundled dependency"):
        relocator.relocate(tmp_path)
