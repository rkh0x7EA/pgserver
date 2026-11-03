from pathlib import Path
import sys
import subprocess
from typing import Optional, List, Callable, Tuple
import logging
import tempfile
import os
from importlib.util import find_spec

def _find_postgres_binaries() -> Tuple[Optional[Path], Optional[int]]:
    """Find the requested major on Python's import path, including namespace portions."""
    major = os.environ.get("PGSERVER_VERSION", "16")
    if major not in ("16", "17", "18"):
        raise ValueError("PGSERVER_VERSION must be 16, 17 or 18")
    spec = find_spec("pgserver_binaries")
    if spec is not None:
        for location in spec.submodule_search_locations or ():
            bin_path = Path(location) / f"pg{major}" / "bin"
            executable = "postgres.exe" if sys.platform == "win32" else "postgres"
            if (bin_path / executable).is_file():
                return bin_path, int(major)
    return None, None

# Find installed PostgreSQL binaries
POSTGRES_BIN_PATH, INSTALLED_POSTGRES_VERSION = _find_postgres_binaries()

_logger = logging.getLogger('pgserver')

def create_command_function(pg_exe_name : str) -> Callable:
    def command(args : List[str], pgdata : Optional[Path] = None, **kwargs) -> str:
        """
            Run a command with the given command line arguments.
            Args:
                args: The command line arguments to pass to the command as a string,
                a list of options as would be passed to `subprocess.run`
                pgdata: The path to the data directory to use for the command.
                    If the command does not need a data directory, this should be None.
                kwargs: Additional keyword arguments to pass to `subprocess.run`, eg user, timeout.

            Returns:
                The stdout of the command as a string.
        """
        if POSTGRES_BIN_PATH is None:
            major = os.environ.get("PGSERVER_VERSION", "16")
            raise FileNotFoundError(f"Install pgserver-postgres-{major} from the matching pgserver release")
        if pg_exe_name.removesuffix('.exe') in ['initdb', 'pg_ctl']:
            if pgdata is None:
                raise ValueError("pgdata must be provided for initdb and pg_ctl")

        if pgdata is not None:
            args = ["-D", str(pgdata)] + args

        full_command_line = [str(POSTGRES_BIN_PATH / pg_exe_name)] + args

        with tempfile.TemporaryFile('w+') as stdout, tempfile.TemporaryFile('w+') as stderr:
            try:
                _logger.info("Running commandline:\n%s\nwith kwargs: `%s`", full_command_line, kwargs)
                # NB: capture_output=True, as well as using stdout=subprocess.PIPE and stderr=subprocess.PIPE
                # can cause this call to hang, even with a time-out depending on the command, (pg_ctl)
                # so we use two temporary files instead
                result = subprocess.run(full_command_line, check=True, stdout=stdout, stderr=stderr, text=True,
                                        **kwargs)
                stdout.seek(0)
                stderr.seek(0)
                output = stdout.read()
                error = stderr.read()
                _logger.info("Successful postgres command %s with kwargs: `%s`\nstdout:\n%s\n---\nstderr:\n%s\n---\n",
                            result.args, kwargs, output, error)
            except subprocess.CalledProcessError as err:
                stdout.seek(0)
                stderr.seek(0)
                output = stdout.read()
                error = stderr.read()
                _logger.error("Failed postgres command %s with kwargs: `%s`:\nerror:\n%s\nstdout:\n%s\n---\nstderr:\n%s\n---\n",
                            err.args, kwargs, str(err), output,  error)
                raise err

        return output

    return command

__all__ = ['INSTALLED_POSTGRES_VERSION', 'POSTGRES_BIN_PATH']


def _init():
    names = {"initdb", "pg_ctl", "psql", "pg_dump", "pg_restore", "pg_config", "postgres"}
    if POSTGRES_BIN_PATH is not None:
        names.update(path.name.removesuffix('.exe') for path in POSTGRES_BIN_PATH.iterdir()
                     if path.is_file() and (path.suffix == '.exe' if sys.platform == 'win32'
                                            else os.access(path, os.X_OK)))
    for name in sorted(names):
        executable = name + ".exe" if sys.platform == "win32" else name
        setattr(sys.modules[__name__], name, create_command_function(executable))
        __all__.append(name)


_init()
