from pathlib import Path
import os
import platform
import sys
from setuptools import Distribution, setup
from setuptools.command.bdist_wheel import bdist_wheel


class BinaryDistribution(Distribution):
    def has_ext_modules(self):
        return True


class BinaryWheel(bdist_wheel):
    def get_tag(self):
        tag = super().get_tag()[2]
        if sys.platform == "darwin":
            target = os.environ.get("MACOSX_DEPLOYMENT_TARGET", "11.0").replace(".", "_")
            tag = f"macosx_{target}_{platform.machine()}"
        return "py3", "none", tag


if not any((Path(__file__).parent / "src/pgserver_binaries/pg17/bin").glob("postgres*")):
    raise RuntimeError("Run make build in this package before building a wheel")

setup(distclass=BinaryDistribution, cmdclass={"bdist_wheel": BinaryWheel})
