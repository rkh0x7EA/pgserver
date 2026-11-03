import pgserver
import psutil
import psycopg
from psycopg import sql
import pytest


@pytest.fixture(scope="session")
def server(tmp_path_factory):
    pg = pgserver.get_server(tmp_path_factory.mktemp("postgres"))
    with psycopg.connect(pg.get_uri(), autocommit=True) as conn:
        conn.execute("CREATE DATABASE test_template")
    with psycopg.connect(pg.get_uri("test_template")) as conn:
        conn.execute("CREATE TABLE template_seed (value int)")
        conn.execute("INSERT INTO template_seed VALUES (42)")
    yield pg
    try:
        processes = [psutil.Process(pg.get_pid())]
        processes += processes[0].children(recursive=True)
        socket = pg.get_postmaster_info().socket_path
    finally:
        pg.cleanup()
    _, alive = psutil.wait_procs(processes, timeout=5)
    assert not alive, f"PostgreSQL processes survived teardown: {alive}"
    assert not (pg.pgdata / "postmaster.pid").exists()
    if socket is not None:
        assert not socket.exists()
        assert not socket.with_name(socket.name + ".lock").exists()


@pytest.fixture
def database(server, worker_id):
    name = "test_" + worker_id
    with psycopg.connect(server.get_uri(), autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {} TEMPLATE test_template").format(sql.Identifier(name)))
    yield server.get_uri(name)
    with psycopg.connect(server.get_uri(), autocommit=True) as conn:
        conn.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
