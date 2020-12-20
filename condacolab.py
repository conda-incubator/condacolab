"""
condacolab
Install Conda and friends on Google Colab, easily

Usage:

>>> import condacolab
>>> condacolab.install()

For more details, check the docstrings for ``install_from_url()``.
"""

import os
import sys
import shutil
from pathlib import Path
from subprocess import call
from typing import Dict, AnyStr
from urllib.request import urlopen
from distutils.spawn import find_executable

from IPython import get_ipython

try:
    import google.colab
except ImportError:
    raise RuntimeError("This module must ONLY run as part of a Colab notebook!")


__VERSION__ = "0.1"
PREFIX = "/usr/local"


def install_from_url(
    installer_url: AnyStr, prefix: os.PathLike = PREFIX, env: Dict[AnyStr, AnyStr] = None
):
    """
    Download and run a constructor-like installer, patching
    the necessary bits so it works on Colab right away.

    This will restart your kernel as a result!

    Parameters
    ----------
    installer_url
        URL pointing to a ``constructor``-like installer, such
        as Miniconda or Mambaforge
    prefix
        Target location for the installation
    env
        Environment variables to inject in the kernel restart.
        We *need* to inject ``LD_LIBRARY_PATH`` so ``{PREFIX}/lib``
        is first, but you can also add more if you need it. Take
        into account that no quote handling is done, so you need
        to add those yourself in the raw string. They will
        end up added to a line like ``exec env VAR=VALUE python3...``.
        For example, a value with spaces should be passed as::

            env={"VAR": '"a value with spaces"'}

    """
    print(f"⏬ Downloading {installer_url}...")
    installer_fn = "_miniconda_installer_.sh"
    with urlopen(installer_url) as response, open(installer_fn, "wb") as out:
        shutil.copyfileobj(response, out)

    print("📦 Installing...")
    call(["bash", installer_fn, "-bfp", str(prefix)])
    os.unlink(installer_fn)

    print("📌 Adjusting configuration...")
    cuda_version = ".".join(os.environ.get("CUDA_VERSION", "*.*.*").split(".")[:2])
    prefix = Path(prefix)
    condameta = prefix / "conda-meta"
    condameta.mkdir(parents=True, exist_ok=True)
    pymaj, pymin = sys.version_info[:2]

    with open(condameta / "pinned", "a") as f:
        f.write(f"python {pymaj}.{pymin}.*\n")
        f.write(f"python_abi {pymaj}.{pymin}.* *cp{pymaj}{pymin}*\n")
        f.write(f"cudatoolkit {cuda_version}.*\n")

    with open(prefix / ".condarc", "a") as f:
        f.write("always_yes: true\n")

    with open("/etc/ipython/ipython_config.py", "a") as f:
        f.write(
            f"""\nc.InteractiveShellApp.exec_lines = [
                    "import sys",
                    "sp = f'{prefix}/lib/python{pymaj}.{pymin}/site-packages'",
                    "if sp not in sys.path:",
                    "    sys.path.insert(0, sp)",
                ]
            """
        )
    sitepackages = f"{prefix}/lib/python{pymaj}.{pymin}/site-packages"
    if sitepackages not in sys.path:
        sys.path.insert(0, sitepackages)

    print("🩹 Patching environment...")
    env = env or {}
    env["LD_LIBRARY_PATH"] = f'"{prefix}/lib:$LD_LIBRARY_PATH"'

    os.rename(sys.executable, f"{sys.executable}.real")
    with open(sys.executable, "w") as f:
        f.write("#!/bin/bash\n")
        envstr = " ".join(f"{k}={v}" for k, v in env.items())
        f.write(f"exec env {envstr} {sys.executable}.real -x $@\n")
    call(["chmod", "+x", sys.executable])

    print("🔁 Restarting kernel...")
    get_ipython().kernel.do_shutdown(True)


def install_mambaforge(prefix: os.PathLike = PREFIX):
    installer_url = r"https://github.com/jaimergp/miniforge/releases/download/refs%2Fpull%2F1%2Fmerge/Mambaforge-colab-Linux-x86_64.sh"
    return install_from_url(installer_url, prefix=prefix)


# Make mambaforge the default
install = install_mambaforge


def install_miniconda(prefix: os.PathLike = PREFIX):
    installer_url = r"https://repo.anaconda.com/miniconda/Miniconda3-4.5.4-Linux-x86_64.sh"
    install_from_url(installer_url, prefix=prefix)


def check(prefix: os.PathLike = PREFIX):
    assert find_executable("conda"), "💥💔💥 Conda not found!"

    pymaj, pymin = sys.version_info[:2]
    sitepackages = f"{prefix}/lib/python{pymaj}.{pymin}/site-packages"
    assert sitepackages in sys.path, f"💥💔💥 PYTHONPATH was not patched! Value: {sys.path}"
    assert (
        f"{prefix}/lib" in os.environ["LD_LIBRARY_PATH"]
    ), f"💥💔💥 LD_LIBRARY_PATH was not patched! Value: {os.environ['LD_LIBRARY_PATH']}"
    print("✨🍰✨ Everything looks OK!")
