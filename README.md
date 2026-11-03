# pgserver: PostgreSQL 16 for Python tests

This fork packages a real PostgreSQL **16.13** server with **pgvector 0.8.1**. The launcher is pure Python; separate binary wheels contain PostgreSQL. Releases are GitHub release assets, **not PyPI releases**. The 16.13 pin matches issue #1's production compatibility target.

| Distribution | Wheel tag | Tested Python |
| --- | --- | --- |
| `pgserver==0.2.0` | `py3-none-any` | CPython 3.12, 3.13, 3.14 |
| `pgserver-postgres-16==0.2.0`, macOS arm64 | `py3-none-macosx_11_0_arm64` | CPython 3.12, 3.13, 3.14 |
| `pgserver-postgres-16==0.2.0`, Linux x86_64 | `py3-none-manylinux_2_28_x86_64` | CPython 3.12, 3.13, 3.14 |

Linux requires glibc 2.28 or newer (not Alpine/musl). macOS binaries target 11.0 or newer; CI runs on the current arm64 runner, not an actual macOS 11 machine. Neither wheel uses the CPython ABI. Windows and Intel macOS are source-build options, without release/test guarantees in this fork; Windows executable discovery remains supported.

## Install from a release, with hashes

Choose a published tag from [Releases](https://github.com/rkh0x7EA/pgserver/releases), for example `v0.2.0-pg16.13` once published. The following example uses macOS arm64; on Linux set `platform=manylinux_2_28_x86_64`. Run it in a fresh venv with pip and [uv](https://docs.astral.sh/uv/) installed:

```sh
release=v0.2.0-pg16.13
platform=macosx_11_0_arm64
base="https://github.com/rkh0x7EA/pgserver/releases/download/$release"
launcher=pgserver-0.2.0-py3-none-any.whl
binary="pgserver_postgres_16-0.2.0-py3-none-$platform.whl"
curl -fL "$base/SHA256SUMS" -o SHA256SUMS
curl -fL "$base/$launcher" -o "$launcher"
curl -fL "$base/$binary" -o "$binary"
awk -v a="$launcher" -v b="$binary" '$2 == a || $2 == b' SHA256SUMS > selected.sha256
test "$(wc -l < selected.sha256 | tr -d ' ')" = 2
shasum -a 256 --check selected.sha256
cat > requirements.in <<EOF
pgserver @ $base/$launcher
pgserver-postgres-16 @ $base/$binary
EOF
uv pip compile --python-version 3.12 --generate-hashes requirements.in -o requirements.lock
# Check the two URL hashes in the lock against the downloaded SHA256SUMS.
python -m pip install --require-hashes -r requirements.lock
```

Commit the reviewed `requirements.lock` in the consumer. It pins the two release URLs and hashes **and every transitive dependency** (`fasteners`, `platformdirs`, `psutil`); pip's hash mode requires all of them. Generate a lock per platform if the consumer's other dependencies differ. Runtime dependency wheels come from PyPI; this fork's two wheels come only from the specified release. A checksum validates bytes against the published manifest, not the publisher's identity.

```python
import pgserver

assert pgserver.INSTALLED_POSTGRES_VERSION == 16
with pgserver.get_server("./test-data") as server:
    print(server.psql("SELECT version()"))
    print(server.get_uri())
# Server stops; data remains. Use cleanup_mode="delete" to remove it too.
```

The parent of the data directory must exist. Unix uses a local socket; Windows uses loopback TCP. These are disposable test servers with trust authentication, not a production deployment. Always close connections and call `cleanup()` (or use a context manager). Normal interpreter exit also invokes cleanup; SIGKILL cannot do so. PostgreSQL's PID/socket lock files disappear on shutdown. The launcher's shared coordination lock intentionally remains: unlinking an interprocess lock can split concurrent callers across different lock files.

`pgserver.POSTGRES_BIN_PATH` exposes the selected `bin` directory; wrappers such as `pgserver.pg_ctl` and `pgserver.pg_restore` invoke those executables directly. No system PATH search or global PATH/LD_LIBRARY_PATH/DYLD changes are needed. Importing without binaries is allowed, but starting a server fails with an installation hint.

## pytest / xdist fixture

Install `pytest`, `pytest-xdist`, and `psycopg[binary]`. Each xdist worker gets its own session server/data directory, initializes a template, and clones its own database. Put this in `conftest.py`:

```python
import pgserver
import psycopg
from psycopg import sql
import pytest

@pytest.fixture(scope="session")
def pg_server(tmp_path_factory, worker_id):
    with pgserver.get_server(tmp_path_factory.mktemp("pg-" + worker_id)) as server:
        with psycopg.connect(server.get_uri(), autocommit=True) as conn:
            conn.execute("CREATE DATABASE test_template")
        with psycopg.connect(server.get_uri("test_template")) as conn:
            conn.execute("CREATE TABLE example (id bigint PRIMARY KEY)")
            # Apply the application's migrations here, before cloning.
        yield server

@pytest.fixture(scope="session")
def database_uri(pg_server, worker_id):
    name = "test_" + worker_id
    with psycopg.connect(pg_server.get_uri(), autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {} TEMPLATE test_template")
                     .format(sql.Identifier(name)))
    yield pg_server.get_uri(name)
    # Tests must close their connections before session teardown.
    with psycopg.connect(pg_server.get_uri(), autocommit=True) as conn:
        conn.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)")
                     .format(sql.Identifier(name)))
```

Run `pytest -n 2`. Use a function-scoped clone fixture instead when each test needs fresh data. The repository's acceptance tests exercise eight simultaneous psycopg 3 sessions, observed row-lock contention and release, native enum/partial unique index DDL, pgvector, and process/PID/socket-lock cleanup.

## Building and optional majors

```sh
python -m pip install build
make wheel PYTHON=python JOBS=4
```

This creates the launcher and PG16 wheels under `dist/`. Building requires a C compiler, GNU make, curl, and the usual PostgreSQL build tools (bison/flex for majors that need generated parser files). Linux also requires `patchelf`. Downloads are SHA-256 checked before extraction; PostgreSQL checksums are pinned from postgresql.org. The pgvector archive hash is pinned in `pgbuild/Makefile`; `OPTFLAGS=` avoids builder-specific CPU instructions. The macOS build targets 11.0 by default and rewrites/signs Mach-O libraries. CI additionally runs delocate's deployment-target/architecture checks. Linux release wheels must be built inside manylinux_2_28 and repaired with auditwheel; merely renaming a Linux wheel is insufficient. Optional readline, ICU and zlib support are disabled to avoid external runtime dependencies.

The launcher depends only on PG16 binaries. `pg17` and `pg18` extras add their corresponding packages; extras are additive, so PG16 remains installed. Their source pins are 17.6 and 18.0. Build these locally with `make wheel PGSERVER_VERSION=17` or `18`, or `make -C packages/pgserver-postgres-17 build` followed by `python -m build --wheel packages/pgserver-postgres-17`. They are not part of this fork's required release matrix.

Select an optional installed major **before importing pgserver**, e.g. `PGSERVER_VERSION=17 python your_test.py`. Default selection is always 16 even with several packages installed; a missing selected major is an error. Never point a different major at an existing cluster without a PostgreSQL upgrade.

CI builds once per OS, tests each wheel on Python 3.12–3.14 (including two xdist workers), and only then publishes three wheels plus `SHA256SUMS` on a `v*` tag. It uses no compiled-build cache and no PyPI publishing credentials. The fork preserves the original work by Oscar Moll and David Bern from upstream PR #13.
