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
from datetime import datetime, timedelta
from glob import glob
from pathlib import Path
from subprocess import run
from typing import Dict, AnyStr, List
from urllib.request import urlopen
from distutils.spawn import find_executable

from IPython import get_ipython

try:
    import google.colab
except ImportError:
    raise RuntimeError("This module must ONLY run as part of a Colab notebook!")


__version__ = "0.1.2"
__author__ = "Jaime Rodríguez-Guerra <jaimergp@users.noreply.github.com>"


PREFIX = "/usr/local"


def install_from_url(
    installer_url: AnyStr,
    prefix: os.PathLike = PREFIX,
    env: Dict[AnyStr, AnyStr] = None,
    run_checks: bool = True,
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

    print("📦 Installing...")
    _run(["bash", installer_fn, "-bfp", str(prefix)])
    os.unlink(installer_fn)

    _configure_environment(prefix, env)

    taken = timedelta(seconds=round((datetime.now() - t0).total_seconds(), 0))
    print(f"⏲ Done in {taken}")

    print("🔁 Restarting kernel...")
    get_ipython().kernel.do_shutdown(True)


def install_mambaforge(
    prefix: os.PathLike = PREFIX, env: Dict[AnyStr, AnyStr] = None, run_checks: bool = True
):
    """
    Install Mambaforge, built for Python 3.7.

    Mambaforge consists of a Miniconda-like distribution optimized
    and preconfigured for conda-forge packages, and includes ``mamba``,
    a faster ``conda`` implementation.

    Unlike the official Miniconda, this is built with the latest ``conda``.

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
    installer_url = r"https://github.com/jaimergp/miniforge/releases/latest/download/Mambaforge-colab-Linux-x86_64.sh"
    install_from_url(installer_url, prefix=prefix, env=env, run_checks=run_checks)


# Make mambaforge the default
install = install_mambaforge


def install_miniforge(
    prefix: os.PathLike = PREFIX, env: Dict[AnyStr, AnyStr] = None, run_checks: bool = True
):
    """
    Install Mambaforge, built for Python 3.7.

    Mambaforge consists of a Miniconda-like distribution optimized
    and preconfigured for conda-forge packages.

    Unlike the official Miniconda, this is built with the latest ``conda``.

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
    installer_url = r"https://github.com/jaimergp/miniforge/releases/latest/download/Miniforge-colab-Linux-x86_64.sh"
    install_from_url(installer_url, prefix=prefix, env=env, run_checks=run_checks)


def install_miniconda(
    prefix: os.PathLike = PREFIX, env: Dict[AnyStr, AnyStr] = None, run_checks: bool = True
):
    """
    Install Miniconda 4.9.2 for Python 3.7.

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
    installer_url = r"https://repo.anaconda.com/miniconda/Miniconda3-py37_4.9.2-Linux-x86_64.sh"
    install_from_url(installer_url, prefix=prefix, env=env, run_checks=run_checks)


def install_anaconda(
    prefix: os.PathLike = PREFIX, env: Dict[AnyStr, AnyStr] = None, run_checks: bool = True
):
    """
    Install Anaconda 2020.02, the last official version built
    for Python 3.7.

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
    installer_url = r"https://repo.anaconda.com/archive/Anaconda3-2020.02-Linux-x86_64.sh"
    install_from_url(installer_url, prefix=prefix, env=env, run_checks=run_checks)


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


def copy_to_drive(
    prefix: os.PathLike,
    filepath: AnyStr = 'condacolab_installation.tar.gz',
    compress_program: AnyStr = 'gzip',
):
    """
    Copy the conda installation to Google Drive.

    Parameters
    ----------
    prefix
        Target location for the ``conda`` installation on Colab.
        This should match the ``prefix`` used for the original install.
    filepath
        Path to use for the ``conda`` tarball on Google Drive.
        Default filename is ``condacolab_installation.tar.gz``, located in
        the base directory of Google Drive.
    compress_program
        Pass to ``--use-compress-program`` flag of ``tar``. This sets
        the compression software. Default is 'gzip'. Conider running
        ``!apt-get -qq install pigz`` in Colab then setting this parameter
        to 'pigz' for faster compression speeds.
    """
    remote_path = _mount_drive(filepath)
    print("➡️ Compressing conda directory and copying to Google Drive...")
    _run(["tar", "-I", compress_program, "-cf", remote_path, prefix])
    print("✔️ Done")


def copy_from_drive(
    prefix: os.PathLike,
    filepath: AnyStr = 'condacolab_installation.tar.gz',
    compress_program: AnyStr = 'gzip',
    env: Dict[AnyStr, AnyStr] = None,
    run_checks: bool = True,
):
    """
    Copy a conda installation from Google Drive and setup on Colab.

    Parameters
    ----------
    prefix
        Target location for the ``conda`` installation on Colab.
        This should match the ``prefix`` used for the original install.
    filepath
        Path of the ``conda`` tarball on Google Drive.
        Default filename is ``condacolab_installation.tar.gz``, located in
        the base directory of Google Drive.
    compress_program
        Pass to ``--use-compress-program`` flag of ``tar``. This sets
        the decompression software. Default is 'gzip'.
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
        Run checks to see if conda is already present in
        prefix directory. Change to False to ignore checks
        and attempt to copy conda from Google Drive.
    """
    if run_checks:
        try:  # run checks to see if conda is already present
            return check(prefix)
        except AssertionError:
            pass  # copy conda from Google Drive

    t0 = datetime.now()
    remote_path = _mount_drive(filepath)
    print("⬅️ Copying conda tarball from Google Drive and extracting...")
    _run(["tar", "-I", compress_program, "-xf", remote_path, "-C", "../"])

    _configure_environment(prefix, env)

    taken = timedelta(seconds=round((datetime.now() - t0).total_seconds(), 0))
    print(f"⏲ Done in {taken}")

    print("🔁 Restarting kernel...")
    get_ipython().kernel.do_shutdown(True)


def _configure_environment(
    prefix: os.PathLike,
    env: Dict[AnyStr, AnyStr],
):
    """
    Configure the environment
    """
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
    bin_path = f"{prefix}/bin"
    if bin_path not in os.environ["PATH"]:
        env["PATH"] = f'"{bin_path}:$PATH"'
    env["LD_LIBRARY_PATH"] = f'"{prefix}/lib:$LD_LIBRARY_PATH"'

    os.rename(sys.executable, f"{sys.executable}.real")
    with open(sys.executable, "w") as f:
        f.write("#!/bin/bash\n")
        envstr = " ".join(f"{k}={v}" for k, v in env.items())
        f.write(f"exec env {envstr} {sys.executable}.real -x $@\n")
    _run(["chmod", "+x", sys.executable])


def _mount_drive(filepath: AnyStr):
    """
    Mount Google Drive then return the path for the colab tarball.
    Glob is used to find correct sub-directory of ``/content/drive``
    (can be ``MyDrive`` or ``My Drive``).
    """
    print("🔗 Open link then paste authentication code into box...")
    google.colab.drive.mount("/content/drive")
    remote_path = glob("/content/drive/*/")[0]
    return (f"{remote_path}{filepath}").replace("//", "/")


def _run(command: List[str]):
    """
    Run subprocess and catch errors.
    """
    result = run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr)
    result.check_returncode()


__all__ = [
    "install",
    "install_from_url",
    "install_mambaforge",
    "install_miniforge",
    "install_miniconda",
    "install_anaconda",
    "check",
    "copy_to_drive",
    "copy_from_drive",
    "PREFIX",
]
