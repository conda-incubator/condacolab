"""
condacolab
Install Conda and friends on Google Colab, easily

Usage:

>>> import condacolab
>>> condacolab.install()

For more details, check the docstrings for ``install_from_url()``.
"""

import hashlib
import os
import sys
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from subprocess import run, PIPE, STDOUT
from typing import Dict, AnyStr
from urllib.request import urlopen
from distutils.spawn import find_executable

from IPython import get_ipython

try:
    import google.colab
except ImportError:
    raise RuntimeError("This module must ONLY run as part of a Colab notebook!")


__version__ = "0.1.9"
__author__ = "Jaime Rodríguez-Guerra <jaimergp@users.noreply.github.com>"


PREFIX = "/usr/local"


def _chunked_sha256(path, chunksize=1_048_576):
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while (chunk := f.read(chunksize)):
            hasher.update(chunk)
    return hasher.hexdigest()


def install_from_url(
    installer_url: AnyStr,
    prefix: os.PathLike = PREFIX,
    env: Dict[AnyStr, AnyStr] = None,
    run_checks: bool = True,
    sha256: AnyStr = None,
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
    run_checks
        Run checks to see if installation was run previously.
        Change to False to ignore checks and always attempt
        to run the installation.
    sha256
        Expected SHA256 checksum of the installer. Optional.
    """
    if run_checks:
        try:  # run checks to see if it this was run already
            return check(prefix)
        except AssertionError:
            pass  # just install

    t0 = datetime.now()
    print(f"⏬ Downloading {installer_url}...")
    installer_fn = "__installer__.sh"
    with urlopen(installer_url) as response, open(installer_fn, "wb") as out:
        shutil.copyfileobj(response, out)

    if sha256 is not None:
        digest = _chunked_sha256(installer_fn)
        assert digest == sha256, f"💥💔💥 Checksum failed! Expected {sha256}, got {digest}"

    print("📦 Installing...")
    task = run(
        ["bash", installer_fn, "-bfp", str(prefix)],
        check=False,
        stdout=PIPE,
        stderr=STDOUT,
        text=True,
    )
    os.unlink(installer_fn)
    with open("condacolab_install.log", "w") as f:
        f.write(task.stdout)
    assert (
        task.returncode == 0
    ), "💥💔💥 The installation failed! Logs are available at `/content/condacolab_install.log`."

    print("📌 Adjusting configuration...")
    cuda_version = ".".join(os.environ.get("CUDA_VERSION", "*.*.*").split(".")[:2])
    prefix = Path(prefix)
    condameta = prefix / "conda-meta"
    condameta.mkdir(parents=True, exist_ok=True)
    pymaj, pymin = sys.version_info[:2]

    if cuda_version.startswith("12"):
        cudatoolkit = "cuda-version 12.*"
    else:
        cudatoolkit = f"cudatoolkit {cuda_version}.*"

    with open(condameta / "pinned", "a") as f:
        f.write(f"python {pymaj}.{pymin}.*\n")
        f.write(f"python_abi {pymaj}.{pymin}.* *cp{pymaj}{pymin}*\n")
        f.write(f"{cudatoolkit}\n")

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
    bin_path = f"{prefix}/bin"
    if bin_path not in os.environ.get("PATH", "").split(":"):
        env["PATH"] = f"{bin_path}:{os.environ.get('PATH', '')}"
    env["LD_LIBRARY_PATH"] = f"{prefix}/lib:{os.environ.get('LD_LIBRARY_PATH', '')}"

    os.rename(sys.executable, f"{sys.executable}.real")
    with open(sys.executable, "w") as f:
        f.write("#!/bin/bash\n")
        envstr = " ".join(f"{k}={v}" for k, v in env.items())
        f.write(f"exec env {envstr} {sys.executable}.real -x $@\n")
    run(["chmod", "+x", sys.executable])

    taken = timedelta(seconds=round((datetime.now() - t0).total_seconds(), 0))
    print(f"⏲ Done in {taken}")

    print("🔁 Restarting kernel...")
    get_ipython().kernel.do_shutdown(True)


def install_mambaforge(
    prefix: os.PathLike = PREFIX, env: Dict[AnyStr, AnyStr] = None, run_checks: bool = True
):
    """
    Install Mambaforge 23.11.0, built for Python 3.10.

    Mambaforge consists of a Miniconda-like distribution optimized
    and preconfigured for conda-forge packages, and includes ``mamba``,
    a faster ``conda`` implementation.

    Parameters
    ----------
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
    run_checks
        Run checks to see if installation was run previously.
        Change to False to ignore checks and always attempt
        to run the installation.
    """
    installer_url = "https://github.com/conda-forge/miniforge/releases/download/23.11.0-0/Mambaforge-23.11.0-0-Linux-x86_64.sh"
    checksum = "3dfdcc162bf0df83b5025608dc2acdbbc575bd416b75701fb5863343c0517a78"
    install_from_url(installer_url, prefix=prefix, env=env, run_checks=run_checks, sha256=checksum)


# Make mambaforge the default
install = install_mambaforge


def install_miniforge(
    prefix: os.PathLike = PREFIX, env: Dict[AnyStr, AnyStr] = None, run_checks: bool = True
):
    """
    Install Miniforge 23.11.0, built for Python 3.10.

    Miniforge consists of a Miniconda-like distribution optimized
    and preconfigured for conda-forge packages.

    Parameters
    ----------
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
    run_checks
        Run checks to see if installation was run previously.
        Change to False to ignore checks and always attempt
        to run the installation.
    """
    installer_url = "https://github.com/conda-forge/miniforge/releases/download/23.11.0-0/Miniforge3-23.11.0-0-Linux-x86_64.sh"
    checksum = "73576b96409ed38a7ca596bece058e8c77c6ef3eab42af7cfdf2ae975e8f3928"
    install_from_url(installer_url, prefix=prefix, env=env, run_checks=run_checks, sha256=checksum)


def install_miniconda(
    prefix: os.PathLike = PREFIX, env: Dict[AnyStr, AnyStr] = None, run_checks: bool = True
):
    """
    Install Miniconda 23.11.0 for Python 3.10.

    Parameters
    ----------
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
    run_checks
        Run checks to see if installation was run previously.
        Change to False to ignore checks and always attempt
        to run the installation.
    """
    installer_url = "https://repo.anaconda.com/miniconda/Miniconda3-py310_23.11.0-2-Linux-x86_64.sh"
    checksum = "35a58b8961e1187e7311b979968662c6223e86e1451191bed2e67a72b6bd0658"
    install_from_url(installer_url, prefix=prefix, env=env, run_checks=run_checks, sha256=checksum)


def install_anaconda(
    prefix: os.PathLike = PREFIX, env: Dict[AnyStr, AnyStr] = None, run_checks: bool = True
):
    """
    Install Anaconda 2023.03, the latest version built
    for Python 3.10 at the time of update.

    Parameters
    ----------
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
    run_checks
        Run checks to see if installation was run previously.
        Change to False to ignore checks and always attempt
        to run the installation.
    """
    installer_url = "https://repo.anaconda.com/archive/Anaconda3-2023.03-1-Linux-x86_64.sh"
    checksum = "95102d7c732411f1458a20bdf47e4c1b0b6c8a21a2edfe4052ca370aaae57bab"
    install_from_url(installer_url, prefix=prefix, env=env, run_checks=run_checks, sha256=checksum)


def check(prefix: os.PathLike = PREFIX, verbose: bool = True):
    """
    Run some basic checks to ensure that ``conda`` has been installed
    correctly

    Parameters
    ----------
    prefix
        Location where ``conda`` was installed (should match the one
        provided for ``install()``.
    verbose
        Print success message if True
    """
    assert find_executable("conda"), "💥💔💥 Conda not found!"

    pymaj, pymin = sys.version_info[:2]
    sitepackages = f"{prefix}/lib/python{pymaj}.{pymin}/site-packages"
    assert sitepackages in sys.path, f"💥💔💥 PYTHONPATH was not patched! Value: {sys.path}"
    assert (
        f"{prefix}/bin" in os.environ["PATH"]
    ), f"💥💔💥 PATH was not patched! Value: {os.environ['PATH']}"
    assert (
        f"{prefix}/lib" in os.environ["LD_LIBRARY_PATH"]
    ), f"💥💔💥 LD_LIBRARY_PATH was not patched! Value: {os.environ['LD_LIBRARY_PATH']}"
    if verbose:
        print("✨🍰✨ Everything looks OK!")


__all__ = [
    "install",
    "install_from_url",
    "install_mambaforge",
    "install_miniforge",
    "install_miniconda",
    "install_anaconda",
    "check",
    "PREFIX",
]
