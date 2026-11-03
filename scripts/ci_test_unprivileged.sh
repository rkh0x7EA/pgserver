#!/usr/bin/env bash
# Run inside the manylinux container as root: create an unprivileged user whose uid matches the
# checkout owner (initdb needs a passwd entry and refuses to run as root), then test as that user.
set -euxo pipefail
uid="$(stat -c %u /io)"
gid="$(stat -c %g /io)"
if [ "$uid" = 0 ]; then uid=1001; gid=1001; fi  # initdb refuses root
getent group "$gid" >/dev/null || groupadd -g "$gid" pgtest
getent passwd "$uid" >/dev/null || useradd -u "$uid" -g "$gid" -M -d /tmp/pgtest-home pgtest
user="$(getent passwd "$uid" | cut -d: -f1)"
mkdir -p /tmp/pgtest-home /tmp/pgserver-runtime
chown "$uid:$gid" /tmp/pgtest-home /tmp/pgserver-runtime
runuser -u "$user" -- env HOME=/tmp/pgtest-home PYTHON_ABI="$PYTHON_ABI" PIP_NO_CACHE_DIR=1 \
  XDG_RUNTIME_DIR=/tmp/pgserver-runtime bash -euxo pipefail -c '
  cd /io
  /opt/python/"$PYTHON_ABI-$PYTHON_ABI"/bin/python -m venv /tmp/test-venv
  export PATH=/tmp/test-venv/bin:$PATH
  python scripts/install_wheels.py wheelhouse
  python -m pip install pytest pytest-xdist pytest-timeout "psycopg[binary]>=3.2" psycopg2-binary "sqlalchemy>=2" sqlalchemy-utils
  python -m pytest --ignore=tests/test_xdist.py -q -p no:cacheprovider
  python -m pytest -n 2 --dist each tests/test_xdist.py -q -p no:cacheprovider
'
