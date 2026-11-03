from importlib.machinery import ModuleSpec
from pathlib import Path
import subprocess
import sys

import pgserver
from pgserver import _commands
import pytest


def test_namespace_selection(tmp_path, monkeypatch):
    portions = [tmp_path / "first", tmp_path / "second"]
    for major, portion in ((18, portions[0]), (16, portions[1]), (17, portions[0])):
        binary = portion / f"pg{major}/bin"
        binary.mkdir(parents=True)
        (binary / ("postgres.exe" if sys.platform == "win32" else "postgres")).touch()
    spec = ModuleSpec("pgserver_binaries", loader=None, is_package=True)
    spec.submodule_search_locations = [str(p) for p in portions]
    monkeypatch.setattr(_commands, "find_spec", lambda _: spec)
    monkeypatch.delenv("PGSERVER_VERSION", raising=False)
    assert _commands._find_postgres_binaries() == (portions[1] / "pg16/bin", 16)
    monkeypatch.setenv("PGSERVER_VERSION", "17")
    assert _commands._find_postgres_binaries() == (portions[0] / "pg17/bin", 17)
    monkeypatch.setenv("PGSERVER_VERSION", "bogus")
    with pytest.raises(ValueError, match="16, 17 or 18"):
        _commands._find_postgres_binaries()


def test_no_binary_package_is_actionable(tmp_path):
    # Load just the command module in isolation, without this venv's site-packages.
    source = Path(_commands.__file__)
    code = f"""
import runpy
commands = runpy.run_path({str(source)!r})
assert commands['POSTGRES_BIN_PATH'] is None
try:
    commands['create_command_function']('initdb')([], pgdata='unused')
except FileNotFoundError as exc:
    assert 'pgserver-postgres-16' in str(exc)
else:
    raise AssertionError('missing binaries did not fail')
"""
    subprocess.run([sys.executable, "-I", "-S", "-c", code], cwd=tmp_path, check=True)


def test_wrapper_names_and_export():
    assert pgserver.POSTGRES_BIN_PATH.is_dir()
    assert "pg_restore" in _commands.__all__
    assert "pg_receivewal" in _commands.__all__


@pytest.mark.parametrize("name", ["postgres", "initdb", "pg_ctl", "psql", "pg_restore", "pg_config"])
def test_installed_executable_versions(name):
    executable = name + ".exe" if sys.platform == "win32" else name
    output = subprocess.check_output([str(pgserver.POSTGRES_BIN_PATH / executable), "--version"], text=True)
    assert "16.13" in output


def test_installed_share_directory():
    shared = Path(pgserver.pg_config(["--sharedir"]).strip())
    assert shared.is_dir()
    assert shared.is_relative_to(pgserver.POSTGRES_BIN_PATH.parent)
    assert (shared / "extension/vector.control").is_file()


def test_failed_start_does_not_cache_instance(tmp_path, monkeypatch):
    def fail(_):
        raise RuntimeError("failed start")
    monkeypatch.setattr(pgserver.PostgresServer, "ensure_pgdata_inited", fail)
    with pytest.raises(RuntimeError, match="failed start"):
        pgserver.get_server(tmp_path)
    assert tmp_path.resolve() not in pgserver.PostgresServer._instances


def test_failed_shutdown_preserves_data_and_can_retry(tmp_path, monkeypatch):
    import os
    from threading import Lock
    from types import SimpleNamespace
    from pgserver import postgres_server
    from pgserver.utils import DiskList

    pg = pgserver.PostgresServer.__new__(pgserver.PostgresServer)
    pg.pgdata = tmp_path / "data"
    pg.pgdata.mkdir()
    pg.global_process_id_list = DiskList(pg.pgdata / ".handle_pids.json")
    pg.global_process_id_list.put([os.getpid()])
    pg.cleanup_mode = "delete"
    pg.system_user = None
    pg._postmaster_info = SimpleNamespace(is_running=lambda: True)
    monkeypatch.setattr(pgserver.PostgresServer, "_lock", Lock())
    monkeypatch.setattr(pgserver.PostgresServer, "_instances", {pg.pgdata: pg})

    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "pg_ctl")
    monkeypatch.setattr(postgres_server, "pg_ctl", fail)
    with pytest.raises(subprocess.CalledProcessError):
        pg.cleanup()
    assert pg.global_process_id_list.get() == [os.getpid()]
    assert pgserver.PostgresServer._instances[pg.pgdata] is pg
    monkeypatch.setattr(postgres_server, "pg_ctl", lambda *args, **kwargs: "")
    pg.cleanup()
    assert not pg.pgdata.exists()
    assert pg.pgdata not in pgserver.PostgresServer._instances


def test_missing_binaries_fail_before_process_setup(tmp_path, monkeypatch):
    from pgserver import postgres_server
    monkeypatch.setattr(postgres_server, "POSTGRES_BIN_PATH", None)
    with pytest.raises(FileNotFoundError, match="Install pgserver-postgres-16"):
        pgserver.get_server(tmp_path)
