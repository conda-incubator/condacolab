"""
condacolab
Install Conda and friends on Google Colab, easily

Usage:

>>> import condacolab
>>> condacolab.install()

For more details, check the docstrings for ``install_from_url()``.
"""

import json
import os
import sys
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from subprocess import check_output, run, PIPE, STDOUT
from textwrap import dedent
from typing import Dict, AnyStr
from urllib.request import urlopen
from distutils.spawn import find_executable
from IPython.display import display

from IPython import get_ipython

try:
    import ipywidgets as widgets
    HAS_IPYWIDGETS = True
except ImportError:
    HAS_IPYWIDGETS = False

try:
    import google.colab
except ImportError:
    raise RuntimeError("This module must ONLY run as part of a Colab notebook!")


__version__ = "0.1.4"
__author__ = (
    "Jaime Rodríguez-Guerra <jaimergp@users.noreply.github.com>, "
    "Surbhi Sharma <ssurbhi560@users.noreply.github.com>"
)


PREFIX = "/opt/conda"

if HAS_IPYWIDGETS:
    restart_kernel_button = widgets.Button(description="Restart kernel now...")
    restart_button_output = widgets.Output(layout={'border': '1px solid black'})
else:
    restart_kernel_button = restart_button_output = None

def _on_button_clicked(b):
  with restart_button_output:
    get_ipython().kernel.do_shutdown(True)
    print("Kernel restarted!")
    restart_kernel_button.close()

def _run_subprocess(command, logs_filename):
    """
    Run subprocess then write the logs for that process and raise errors if it fails.

    Parameters
    ----------
    command
        Command to run while installing the packages.

    logs_filename
        Name of the file to be used for writing the logs after running the task.
    """

    task = run(
            command,
            check=False,
            stdout=PIPE,
            stderr=STDOUT,
            text=True,
        )

    logs_file_path = "/var/condacolab"
    os.makedirs(logs_file_path, exist_ok=True)

    with open(f"{logs_file_path}/{logs_filename}", "w") as f:
        f.write(task.stdout)
    assert (task.returncode == 0), f"💥💔💥 The installation failed! Logs are available at `{logs_file_path}/{logs_filename}`."


def install_from_url(
    installer_url: AnyStr,
    prefix: os.PathLike = PREFIX,
    env: Dict[AnyStr, AnyStr] = None,
    run_checks: bool = True,
    restart_kernel: bool = True,
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
    restart_kernel
        Variable to manage the kernel restart during the installation 
        of condacolab. Set it `False` to stop the kernel from restarting 
        automatically and get a button instead to do it.
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

    condacolab_task = _run_subprocess(
        ["bash", installer_fn, "-bfp", str(prefix)],
        "condacolab_install.log",
        )

    print("📌 Adjusting configuration...")
    cuda_version = ".".join(os.environ.get("CUDA_VERSION", "*.*.*").split(".")[:2])
    prefix = Path(prefix)
    condameta = prefix / "conda-meta"
    condameta.mkdir(parents=True, exist_ok=True)

    with open(condameta / "pinned", "a") as f:
        f.write(f"cudatoolkit {cuda_version}.*\n")

    with open(prefix / ".condarc", "a") as f:
        f.write("always_yes: true\n")

    print("📦 Installing...")

# Installing the following packages because Colab server expects these packages to be installed in order to launch a Python kernel:
#     - matplotlib-base
#     - psutil
#     - google-colab
#     - colabtools

    conda_exe = "mamba" if os.path.isfile(f"{prefix}/bin/mamba") else "conda"

    # check if any of those packages are already installed. If it is installed, remove it from the list of required packages.

    output = check_output([f"{prefix}/bin/conda", "list", "--json"])
    payload = json.loads(output)
    installed_names = [pkg["name"] for pkg in payload] 
    required_packages = ["matplotlib-base", "psutil", "google-colab"]
    for pkg in required_packages.copy():
        if pkg in installed_names:
            required_packages.remove(pkg)

    if required_packages:
        _run_subprocess(
            [f"{prefix}/bin/{conda_exe}", "install", "-yq", *required_packages],
            "conda_task.log",
        )

    pip_task = _run_subprocess(
        [f"{prefix}/bin/python", "-m", "pip", "-q", "install", "-U", "https://github.com/googlecolab/colabtools/archive/refs/heads/main.zip", "condacolab"],
        "pip_task.log"
        )

    env = env or {}
    bin_path = f"{prefix}/bin"

    os.rename(sys.executable, f"{sys.executable}.renamed_by_condacolab.bak")
    with open(sys.executable, "w") as f:
        f.write(
            dedent(
                f"""
                #!/bin/bash
                source {prefix}/etc/profile.d/conda.sh
                conda activate
                unset PYTHONPATH
                mv /usr/bin/lsb_release /usr/bin/lsb_release.renamed_by_condacolab.bak
                exec {bin_path}/python $@
                """
            ).lstrip()
        )
    run(["chmod", "+x", sys.executable])

    taken = timedelta(seconds=round((datetime.now() - t0).total_seconds(), 0))
    print(f"⏲ Done in {taken}")

    if restart_kernel:
        print("🔁 Restarting kernel...")
        get_ipython().kernel.do_shutdown(True)

    elif HAS_IPYWIDGETS:
        print("🔁 Please restart kernel...")
        restart_kernel_button.on_click(_on_button_clicked)
        display(restart_kernel_button, restart_button_output)

    else:
        print("🔁 Please restart kernel by clicking on Runtime > Restart runtime.")

def install_from_local(
    installer_path: str,
    prefix: os.PathLike = PREFIX,
    env: Dict[AnyStr, AnyStr] = None,
    run_checks: bool = True,
    restart_kernel: bool = True,
):
    """
    Install conda from a local file (instead of a URL), such as a custom constructor installer.

    Parameters
    ----------
    installer_path : str
        Path to the local `.sh` installer file.
    prefix : Path
        Target installation directory.
    env : dict
        Environment variables to inject into the restarted kernel.
        LD_LIBRARY_PATH must include `{PREFIX}/lib`, but you can add more.
        Note: No automatic quoting is done, so values with spaces must be quoted manually.
        For example: env={"VAR": '"value with spaces"'}
    run_checks : bool
        Whether to run pre-installation checks. Set to False to force installation.
    restart_kernel : bool
        Whether to restart the kernel automatically after installation.
    """
    if run_checks:
        try:
            return check(prefix)
        except AssertionError:
            pass  # proceed with installation

    t0 = datetime.now()
    print(f"📁 Using local installer: {installer_path}")

    _run_subprocess(
        ["bash", installer_path, "-bfp", str(prefix)],
        "condacolab_install.log",
    )

    print("📌 Adjusting configuration...")
    cuda_version = ".".join(os.environ.get("CUDA_VERSION", "*.*.*").split(".")[:2])
    prefix = Path(prefix)
    condameta = prefix / "conda-meta"
    condameta.mkdir(parents=True, exist_ok=True)

    with open(condameta / "pinned", "a") as f:
        f.write(f"cudatoolkit {cuda_version}.*\n")

    with open(prefix / ".condarc", "a") as f:
        f.write("always_yes: true\n")

    print("📦 Installing base packages...")

    # Installing the following packages because Colab server expects these packages to be installed in order to launch a Python kernel:
    #     - matplotlib-base
    #     - psutil
    #     - google-colab
    #     - colabtools

    conda_exe = "mamba" if os.path.isfile(f"{prefix}/bin/mamba") else "conda"
    
    # check if any of those packages are already installed. If it is installed, remove it from the list of required packages.
    
    output = check_output([f"{prefix}/bin/conda", "list", "--json"])
    payload = json.loads(output)
    installed_names = [pkg["name"] for pkg in payload]
    required_packages = ["matplotlib-base", "psutil", "google-colab"]

    for pkg in required_packages.copy():
        if pkg in installed_names:
            required_packages.remove(pkg)

    if required_packages:
        _run_subprocess(
            [f"{prefix}/bin/{conda_exe}", "install", "-yq", *required_packages],
            "conda_task.log",
        )

    pip_task = _run_subprocess(
        [f"{prefix}/bin/python", "-m", "pip", "-q", "install", "-U", 
         "https://github.com/googlecolab/colabtools/archive/refs/heads/main.zip", 
         "condacolab"],
        "pip_task.log"
        )
    env = env or {}
    bin_path = f"{prefix}/bin"
    
    os.rename(sys.executable, f"{sys.executable}.renamed_by_condacolab.bak")
    with open(sys.executable, "w") as f:
        f.write(
            dedent(
                f"""
                #!/bin/bash
                source {prefix}/etc/profile.d/conda.sh
                conda activate
                unset PYTHONPATH
                mv /usr/bin/lsb_release /usr/bin/lsb_release.renamed_by_condacolab.bak
                exec {bin_path}/python $@
                """
            ).lstrip()
        )
    run(["chmod", "+x", sys.executable])

    taken = timedelta(seconds=round((datetime.now() - t0).total_seconds(), 0))
    print(f"⏲ Done in {taken}")

    if restart_kernel:
        print("🔁 Restarting kernel...")
        get_ipython().kernel.do_shutdown(True)
    elif HAS_IPYWIDGETS:
        print("🔁 Please restart kernel manually...")
        restart_kernel_button.on_click(_on_button_clicked)
        display(restart_kernel_button, restart_button_output)
    else:
        print("🔁 Please restart kernel from Runtime > Restart runtime.")


def install_mambaforge(*args, **kwargs):
    print(
        "Mambaforge has been superseded by Miniforge.",
        "Use `install_miniforge()` to remove this warning.",
        file=sys.stderr,
    )
    return install_miniforge(*args, **kwargs)


def install_miniforge(
    prefix: os.PathLike = PREFIX, env: Dict[AnyStr, AnyStr] = None, run_checks: bool = True, restart_kernel: bool = True,
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
    restart_kernel
        Variable to manage the kernel restart during the installation 
        of condacolab. Set it `False` to stop the kernel from restarting 
        automatically and get a button instead to do it.
    """
    installer_url = r"https://github.com/jaimergp/miniforge/releases/latest/download/Miniforge-colab-Linux-x86_64.sh"
    install_from_url(installer_url, prefix=prefix, env=env, run_checks=run_checks, restart_kernel=restart_kernel)


# Make miniforge the default
install = install_miniforge


def install_miniconda(
    prefix: os.PathLike = PREFIX, env: Dict[AnyStr, AnyStr] = None, run_checks: bool = True, restart_kernel: bool = True,
):
    """
    Install Miniconda 4.12.0 for Python 3.7.

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
    restart_kernel
        Variable to manage the kernel restart during the installation 
        of condacolab. Set it `False` to stop the kernel from restarting 
        automatically and get a button instead to do it.
    """
    installer_url = r"https://repo.anaconda.com/miniconda/Miniconda3-py37_4.12.0-Linux-x86_64.sh"
    install_from_url(installer_url, prefix=prefix, env=env, run_checks=run_checks, restart_kernel=restart_kernel)


def install_anaconda(
    prefix: os.PathLike = PREFIX, env: Dict[AnyStr, AnyStr] = None, run_checks: bool = True, restart_kernel: bool = True,
):
    """
    Install Anaconda 2022.05, the latest version built
    for Python 3.7 at the time of update.

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
    restart_kernel
        Variable to manage the kernel restart during the installation 
        of condacolab. Set it `False` to stop the kernel from restarting 
        automatically and get a button instead to do it.
    """
    installer_url = r"https://repo.anaconda.com/archive/Anaconda3-2022.05-Linux-x86_64.sh"
    install_from_url(installer_url, prefix=prefix, env=env, run_checks=run_checks, restart_kernel=restart_kernel)


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
    assert all(
        not path.startswith("/usr/local/") for path in sys.path
    ), f"💥💔💥 PYTHONPATH include system locations: {[path for path in sys.path if path.startswith('/usr/local')]}!"
    assert (
        f"{prefix}/bin" in os.environ["PATH"]
    ), f"💥💔💥 PATH was not patched! Value: {os.environ['PATH']}"
    assert (
        prefix == os.environ.get("CONDA_PREFIX")
    ), f"💥💔💥 CONDA_PREFIX value: {os.environ.get('CONDA_PREFIX', '<not set>')} does not match conda installation location {prefix}!"

    if verbose:
        print("✨🍰✨ Everything looks OK!")


__all__ = [
    "install",
    "install_from_url",
    "install_from_local",
    "install_mambaforge",
    "install_miniforge",
    "install_miniconda",
    "install_anaconda",
    "check",
    "PREFIX",
]
