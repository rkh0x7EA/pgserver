# Changelog

## 0.2.0 — fork PG16 release (unreleased)

- Default to PostgreSQL 16.13 with pgvector 0.8.1; keep 17.6/18.0 source packages opt-in.
- Pure Python launcher and ABI-independent platform binary wheels.
- Verified source archives, per-major builds, relocatable libraries and audited platform tags.
- Deterministic namespace discovery, explicit major selection, actionable missing-binary errors.
- GitHub release wheels and SHA256SUMS, tested on CPython 3.12–3.14, macOS arm64 and manylinux_2_28 x86_64.
- psycopg 3 concurrency, row locks, DDL, clean shutdown and xdist isolation tests.

Based on David Bern's upstream orm011/pgserver#13 (ee018b2), which introduced
separate PostgreSQL 16/17/18 binary packages and removed the dummy CFFI extension.
