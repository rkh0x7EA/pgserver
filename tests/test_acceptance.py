from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import time

import pgserver
import psycopg
import pytest


def test_version_and_template(database):
    assert pgserver.INSTALLED_POSTGRES_VERSION == 16
    with psycopg.connect(database) as conn:
        assert conn.execute("SHOW server_version").fetchone()[0].split()[0] == "16.13"
        assert conn.execute("SELECT value FROM template_seed").fetchone() == (42,)


def test_eight_simultaneous_connections(database):
    barrier = Barrier(8, timeout=15)

    def query(_):
        with psycopg.connect(database, connect_timeout=5) as conn:
            pid = conn.execute("SELECT pg_backend_pid()").fetchone()[0]
            barrier.wait()
            assert conn.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()").fetchone()[0] >= 8
            barrier.wait()
            return pid

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert len(set(pool.map(query, range(8)))) == 8


def test_for_update_contention(database):
    with psycopg.connect(database) as setup:
        setup.execute("CREATE TABLE counter (id int PRIMARY KEY, value int)")
        setup.execute("INSERT INTO counter VALUES (1, 0)")
    with psycopg.connect(database) as first, psycopg.connect(database) as second:
        first.execute("SELECT * FROM counter WHERE id = 1 FOR UPDATE")
        waiter_pid = second.info.backend_pid

        def wait_for_row():
            second.execute("SET statement_timeout = '10s'")
            second.execute("SELECT * FROM counter WHERE id = 1 FOR UPDATE")
            value = second.execute("UPDATE counter SET value = value + 1 RETURNING value").fetchone()[0]
            second.commit()
            return value

        with ThreadPoolExecutor(max_workers=1) as pool:
            waiting = pool.submit(wait_for_row)
            try:
                with psycopg.connect(database, autocommit=True) as observer:
                    deadline = time.monotonic() + 5
                    while True:
                        blocked = observer.execute("SELECT %s = ANY(pg_blocking_pids(%s))", (first.info.backend_pid, waiter_pid)).fetchone()[0]
                        if blocked:
                            break
                        assert time.monotonic() < deadline, "Second session never waited on the row lock"
                        time.sleep(0.02)
                assert not waiting.done()
                first.execute("UPDATE counter SET value = value + 1 WHERE id = 1")
            finally:
                first.commit()
            assert waiting.result(timeout=10) == 2


def test_enum_partial_unique_index_and_vector(database):
    with psycopg.connect(database, autocommit=True) as conn:
        conn.execute("CREATE TYPE job_state AS ENUM ('active', 'done')")
        conn.execute("CREATE TABLE jobs (key text, state job_state)")
        conn.execute("CREATE UNIQUE INDEX active_job ON jobs (key) WHERE state = 'active'")
        conn.execute("INSERT INTO jobs VALUES ('a', 'done'), ('a', 'done'), ('a', 'active')")
        with pytest.raises(psycopg.errors.UniqueViolation):
            conn.execute("INSERT INTO jobs VALUES ('a', 'active')")
        with pytest.raises(psycopg.errors.InvalidTextRepresentation):
            conn.execute("INSERT INTO jobs VALUES ('b', 'invalid')")
        conn.execute("CREATE EXTENSION vector")
        assert conn.execute("SELECT '[1,2,3]'::vector <-> '[1,2,4]'::vector").fetchone() == (1.0,)


def test_paths_and_sql_errors(tmp_path):
    with pgserver.get_server(tmp_path / "data space ' quote") as pg:
        assert "42" in pg.psql("SELECT 42")
        import subprocess
        with pytest.raises(subprocess.CalledProcessError):
            pg.psql("SELECT missing_column")
