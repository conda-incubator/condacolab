"""
condacolab
Install conda packages on Google Colab, easily

Usage:

>>> import condacolab
>>> condacolab.install()

"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from functools import cache
from textwrap import dedent

try:
    import google.colab  # noqa
except ImportError:
    raise RuntimeError("This module must ONLY run as part of a Colab notebook!")

__version__ = "0.2.0a"  # Keep in sync with pyproject.toml

PIXI_DIR = Path("/content")
COLAB_PYTHON_VERSION = ".".join(map(str, sys.version_info[:2]))
DEBUG = os.environ.get("CONDACOLAB_DEBUG", "") == "1"


def _stream_subprocess(cmd, **kwargs) -> None:
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        **kwargs,
    )

    if DEBUG:
        for line in iter(process.stdout.readline, ""):
            sys.stdout.write("    " + line)
            sys.stdout.flush()

    process.wait()
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, cmd)


@cache
def _pixi() -> Path:
    """
    Ensures Pixi is available
    """
    if executable := shutil.which("pixi"):
        return Path(executable)
    _stream_subprocess(
        "curl -fsSL https://pixi.sh/install.sh | PIXI_BIN_DIR=/usr/local/bin bash",
        shell=True,
    )
    return Path("/usr/local/bin/pixi")


def _pixi_toml(
    python_version: str = COLAB_PYTHON_VERSION,
    dependencies: dict[str, str] | None = None,  # TODO
    pypi_dependencies: dict[str, str] | None = None,  # TODO
) -> Path:
    # 2. Populate pixi.toml Manifest
    PIXI_DIR.mkdir(exist_ok=True, parents=True)
    pixi_toml_path = PIXI_DIR / "pixi.toml"

    cuda_version = os.environ.get("CUDA_VERSION", "*.*.*").split(".")[:2]
    if cuda_version[0] == "11":
        cuda_pin = f'cudatoolkit = "{cuda_version[0]}.{cuda_version[1]}.*"'
    else:
        # Assume forward compatibility on major version
        cuda_pin = f'cuda-version = "{cuda_version[0]}.*"'

    pixi_config = dedent(
        f"""\
        [workspace]
        name = "colab-pixi-kernel"
        version = "0.1.0"
        channels = ["conda-forge"]
        platforms = ["linux-64"]

        # These dependencies must be kept more or less in sync with
        # https://github.com/googlecolab/backend-info
        # Debug from Colab's terminal with:
        #  - python3 -m colab_kernel_launcher
        #  - python3 -m google.colab._kernel

        [dependencies]
        python = "{python_version}.*"
        pip = "*"
        pillow = "*"
        matplotlib-base = "*"
        pandas = "2.*"
        httplib2 = "*"
        google-auth = "2.*"
        portpicker = "1.*"
        requests = "2.*"
        tornado = "6.*"

        [constraints]
        {cuda_pin}

        [pypi-dependencies]
        ipython = "==7.*"
        ipykernel = "==6.*"
        ipyparallel = "==8.*"
        jupyter-server = "==2.*"
        anywidget = "*"
        ipython_genutils = "*"

        # Can't be a pypi-dependencies entry because its requirements are way too strict
        [tasks]
        install-google-colab = "pip install https://github.com/googlecolab/colabtools/archive/refs/heads/main.zip --no-deps"
        """
    )
    pixi_toml_path.write_text(pixi_config)
    if DEBUG:
        print("    Wrote", pixi_toml_path)
    return pixi_toml_path


def _pixi_install() -> None:
    _stream_subprocess(
        [_pixi(), "install"],
        cwd=PIXI_DIR,
    )
    _stream_subprocess(
        [_pixi(), "run", "install-google-colab"],
        cwd=PIXI_DIR,
    )


@cache
def _pixi_python() -> Path:
    pixi_python_bin = Path(PIXI_DIR, ".pixi", "envs", "default", "bin", "python")

    if not os.path.exists(pixi_python_bin):
        raise FileNotFoundError(f"Expected Python binary at {pixi_python_bin}")
    return pixi_python_bin


def _forward_kernel_python() -> None:
    backup_python = f"{sys.executable}.orig"
    if not os.path.exists(backup_python):
        shutil.move(sys.executable, f"{sys.executable}.orig")
    Path(sys.executable).write_text(
        dedent(
            f"""\
            #!/bin/bash
            # Patched by condacolab. Original file available at '{sys.executable}.orig'
            eval "$({_pixi()} shell-hook --shell bash)"
            exec "{_pixi_python()}" "$@"
            """
        )
    )
    subprocess.check_call(["chmod", "+x", sys.executable])
    if DEBUG:
        print("    Forwarded", sys.executable, "to activated", _pixi_python())


def _post_install(python_version: str = COLAB_PYTHON_VERSION) -> None:
    import colab_kernel_launcher

    target_site_packages = os.path.join(
        PIXI_DIR,
        ".pixi",
        "envs",
        "default",
        "lib",
        f"python{python_version}",
        "site-packages",
    )
    for module in (colab_kernel_launcher.__file__,):
        try:
            shutil.copy(module, target_site_packages)
        except shutil.SameFileError:
            continue
        else:
            if DEBUG:
                print("    Copied", module, "into", target_site_packages)


def _restart_kernel() -> None:
    from IPython import get_ipython

    get_ipython().kernel.do_shutdown(True)


def install(
    python_version: str = COLAB_PYTHON_VERSION, restart_kernel: bool = True
) -> None:
    """
    Creates a new conda environment with Pixi, including the dependencies
    required to launch a new kernel.

    Parameters
    ----------
    python_version
        Defaults to whatever Colab ships. MUST be a string of format `major.minor`.
    restart_kernel
        Whether to issue an automated kernel restart or ask the user to do it.
    """
    print("📝 Writing pixi.toml...")
    _pixi_toml(python_version=python_version)
    print("📦 Installing...")
    _pixi_install()
    print("✨ Last touches...")
    _post_install(python_version=python_version)
    _forward_kernel_python()
    if restart_kernel:
        print("✅ Done! Restarting kernel...")
        _restart_kernel()
    else:
        print("✅ Done! Please restart kernel via Runtime> Restart session.")

    print(
        "ℹ️ [INFO]",
        f"  Once the session reconnects, you will be running a new Python v{python_version}.",
        "  You can install new packages by running pixi in new cells like this:",
        "    !pixi add <name>",
        sep="\n",
    )


__all__ = ["install"]


def deprecated(*args, **kwargs):
    print(
        "This function has been deprecated. If you still need it, install condacolab==0.1",
        file=sys.stderr,
    )


install_anaconda = install_from_url = install_miniforge = install_miniconda = check = (
    deprecated
)

__all__ = [
    "install",
    "install_from_url",
    "install_miniforge",
    "install_miniconda",
    "install_anaconda",
    "check",
]
