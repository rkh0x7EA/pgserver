import json
import os
import time

import psycopg
import pytest

pytestmark = pytest.mark.skipif("PYTEST_XDIST_WORKER" not in os.environ, reason="Run this file with pytest -n 2 --dist each")


def test_worker_isolation(server, database, worker_id, tmp_path_factory):
    shared = tmp_path_factory.getbasetemp().parent
    (shared / f"worker-{worker_id}.json").write_text(json.dumps([str(server.pgdata), server.get_pid()]))
    deadline = time.monotonic() + 20
    while len(list(shared.glob("worker-*.json"))) < 2:
        assert time.monotonic() < deadline, "Both workers must start independent servers"
        time.sleep(0.05)
    records = [json.loads(p.read_text()) for p in shared.glob("worker-*.json")]
    assert len({row[0] for row in records}) == 2
    assert len({row[1] for row in records}) == 2
    with psycopg.connect(database) as conn:
        assert conn.execute("SELECT value FROM template_seed").fetchone() == (42,)
