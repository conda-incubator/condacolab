"""
condacolab
Install Conda and friends on Google Colab, easily

Usage:

>>> import condacolab
>>> condacolab.install()

For more details, check the docstrings for ``install_from_url()``.
"""

from __future__ import annotations

import json
import hashlib
import os
import shlex
import sys
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from subprocess import check_output, run, PIPE, STDOUT
from textwrap import dedent
from typing import Dict, AnyStr, Iterable
from urllib.request import HTTPError, urlopen


import ipywidgets as widgets
from IPython.display import display
from IPython import get_ipython
from ruamel.yaml import YAML, CommentedMap

try:
    import google.colab  # noqa
except ImportError:
    raise RuntimeError("This module must ONLY run as part of a Colab notebook!")

__version__ = "0.1.12"  # Keep in sync with pyproject.toml

PREFIX = "/opt/conda"
TARGET_PYTHON = "3.12"  # Keep in sync with pyproject.toml

yaml = YAML()
restart_kernel_button = widgets.Button(description="Restart kernel now...")
restart_button_output = widgets.Output(layout={"border": "1px solid black"})


def _on_button_clicked(b):
    with restart_button_output:
        get_ipython().kernel.do_shutdown(True)
        print("Kernel restarted!")
        restart_kernel_button.close()


def _run_subprocess(command, logs_filename) -> None:
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
    assert task.returncode == 0, (
        f"💥💔💥 The installation failed! Logs are available at `{logs_file_path}/{logs_filename}`."
    )


def _update_environment(
    prefix: os.PathLike = PREFIX,
    environment_file: str = None,
    python_version: str = None,
    specs: Iterable[str] = (),
    channels: Iterable[str] = (),
    pip_args: Iterable[str] = (),
    extra_conda_args: Iterable[str] = (),
    conda_exe: str = "conda",
):
    """
    Install the dependencies in conda base environment during
    the condacolab installion.

    Parameters
    ----------
    prefix
        Target location for the installation.
    environment_file
        Path or URL of the environment.yaml file to use for
        updating the conda base enviornment.
    python_version
        Python version to use in the conda base environment, eg. "3.9".
    specs
        List of additional specifications (packages) to install.
    channels
        Comma separated list of channels to use in the conda
        base environment.
    pip_args
        List of additional packages to be installed using pip.
    extra_conda_args
        Any extra conda arguments to be used during the installation.
    """
    os.makedirs("/var/condacolab", exist_ok=True)
    environment_file_path = "/var/condacolab/environment.yaml"

    # When environment.yaml file is not provided.
    if environment_file is None:
        env_details = {}
        if channels:
            env_details["channels"] = channels
        if specs:
            env_details["dependencies"] = specs
        if python_version:
            env_details["dependencies"] += [f"python={python_version}"]
        if pip_args:
            pip_args_dict = {"pip": pip_args}
            env_details["dependencies"].append(pip_args_dict)

        with open(environment_file_path, "w") as f:
            yaml.indent(mapping=2, sequence=4, offset=2)
            yaml.dump(env_details, f)
    else:
        # If URL is given for environment.yaml file
        if environment_file.startswith(("http://", "https://")):
            try:
                with (
                    urlopen(environment_file) as response,
                    open(environment_file_path, "wb") as out,
                ):
                    shutil.copyfileobj(response, out)
            except HTTPError as e:
                raise HTTPError(
                    "The URL you entered is not working, please check it again."
                ) from e

        # If path is given for environment.yaml file
        else:
            shutil.copy(environment_file, environment_file_path)

        with open(environment_file_path, "r") as f:
            env_details = yaml.load(f.read())

        for key in env_details:
            if channels and key == "channels":
                env_details["channels"].extend(channels)
            if key == "dependencies":
                if specs:
                    env_details["dependencies"].extend(specs)
                if python_version:
                    env_details["dependencies"].extend([f"python={python_version}"])
                if pip_args:
                    for element in env_details["dependencies"]:
                        # if pip dependencies are already specified.
                        if isinstance(element, CommentedMap) and "pip" in element:
                            element["pip"].extend(pip_args)
                            break
                        # if there are no pip dependencies specified in the yaml file.
                    else:
                        pip_args_dict = CommentedMap([("pip", [*pip_args])])
                        env_details["dependencies"].append(pip_args_dict)

        with open(environment_file_path, "w") as f:
            f.truncate(0)
            yaml.dump(env_details, f)

    _run_subprocess(
        [
            conda_exe,
            "env",
            "update",
            "-n",
            "base",
            "-f",
            environment_file_path,
            *extra_conda_args,
        ],
        "environment_file_update.log",
    )


def _chunked_sha256(path: str | Path, chunksize: int = 1_048_576) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunksize):
            hasher.update(chunk)
    return hasher.hexdigest()


def _check_python() -> None:
    colab_python = ".".join(map(str, sys.version_info[:2]))
    assert colab_python == TARGET_PYTHON, (
        f"💥💔💥 Colab's Python ({colab_python}) does not match expected version: {TARGET_PYTHON}. "
        "Consider running a different Runtime Version to make them match. More information: "
        "https://github.com/conda-incubator/condacolab/issues/79"
    )


def _colab_kernel_launcher() -> str:
    import colab_kernel_launcher

    return colab_kernel_launcher.__file__


def install_from_url(
    installer_url: AnyStr,
    prefix: os.PathLike = PREFIX,
    env: Dict[AnyStr, AnyStr] = None,
    pre_conda: str = None,
    run_checks: bool = True,
    restart_kernel: bool = True,
    environment_file: str = None,
    python_version: str = None,
    specs: Iterable[str] = (),
    channels: Iterable[str] = (),
    pip_args: Iterable[str] = (),
    extra_conda_args: Iterable[str] = (),
    sha256: str | None = None,
) -> None:
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
    pre_conda
        Shell script to run before activating the conda base environment.
        Accepts a file path or a string with the contents.
    run_checks
        Run checks to see if installation was run previously.
        Change to False to ignore checks and always attempt
        to run the installation.
    restart_kernel
        Variable to manage the kernel restart during the installation
        of condacolab. Set it `False` to stop the kernel from restarting
        automatically and get a button instead to do it.
    sha256
        Expected SHA256 checksum of the installer. Optional.
    """
    if run_checks:
        try:  # run checks to see if it this was run already
            return check(prefix)
        except AssertionError:
            pass  # just install

    _check_python()

    t0 = datetime.now()
    print(f"⏬ Downloading {installer_url}...")
    installer_fn = "__installer__.sh"
    with urlopen(installer_url) as response, open(installer_fn, "wb") as out:
        shutil.copyfileobj(response, out)

    if sha256 is not None:
        digest = _chunked_sha256(installer_fn)
        assert digest == sha256, (
            f"💥💔💥 Checksum failed! Expected {sha256}, got {digest}"
        )

    print("📦 Installing...")
    _run_subprocess(
        ["bash", installer_fn, "-bfp", str(prefix)],
        "condacolab_install.log",
    )
    os.unlink(installer_fn)

    print("📌 Adjusting configuration...")
    cuda_version = os.environ.get("CUDA_VERSION", "*.*.*").split(".")[:2]
    prefix = Path(prefix)
    condameta = prefix / "conda-meta"
    condameta.mkdir(parents=True, exist_ok=True)

    if cuda_version[0] == "11":
        cuda_pin = f"cudatoolkit {cuda_version[0]}.{cuda_version[1]}.*"
    else:
        # Assume forward compatibility on major version
        cuda_pin = f"cuda-version {cuda_version[0]}.*"

    pymaj, pymin = sys.version_info[:2]
    with open(condameta / "pinned", "a") as f:
        f.write(f"python {pymaj}.{pymin}.*\n")
        f.write(f"python_abi {pymaj}.{pymin}.* *cp{pymaj}{pymin}*\n")
        f.write(f"{cuda_pin}\n")

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

    _run_subprocess(
        [
            f"{prefix}/bin/python",
            "-m",
            "pip",
            "-q",
            "install",
            "-U",
            "https://github.com/googlecolab/colabtools/archive/refs/heads/main.zip",
            "condacolab",
        ],
        "pip_task.log",
    )

    print("📦 Updating environment using YAML file...")

    _update_environment(
        prefix=prefix,
        environment_file=environment_file,
        specs=specs,
        channels=channels,
        python_version=python_version,
        pip_args=pip_args,
        extra_conda_args=extra_conda_args,
        conda_exe=f"{prefix}/bin/{conda_exe}",
    )

    env = env or {}
    bin_path = f"{prefix}/bin"
    pre_conda_contents = ""

    if env:
        pre_conda_contents = "".join(
            [f'export {key}="{shlex.quote(value)}"\n' for key, value in env.items()]
        )

    if pre_conda:
        if os.path.isfile(pre_conda):
            with open(pre_conda, "r") as f:
                pre_conda_contents += f.read()
        else:
            pre_conda_contents += str(pre_conda)

    if os.path.exists(sys.executable):
        os.rename(sys.executable, f"{sys.executable}.renamed_by_condacolab.bak")

    with open(sys.executable, "w") as f:
        f.write(
            dedent(
                f"""
                #!/bin/bash
                {pre_conda_contents}
                source "{prefix}/etc/profile.d/conda.sh"
                conda activate
                unset PYTHONPATH
                mv /usr/bin/lsb_release /usr/bin/lsb_release.renamed_by_condacolab.bak
                cp "{_colab_kernel_launcher()}" "{prefix}/lib/python{pymaj}.{pymin}/site-packages"
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
    else:
        print("🔁 Please restart kernel...")
        restart_kernel_button.on_click(_on_button_clicked)
        display(restart_kernel_button, restart_button_output)


def check(prefix: str | Path = PREFIX, verbose: bool = True) -> None:
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
    assert shutil.which("conda"), "💥💔💥 Conda not found!"

    pymaj, pymin = sys.version_info[:2]
    sitepackages = f"{prefix}/lib/python{pymaj}.{pymin}/site-packages"
    assert sitepackages in sys.path, (
        f"💥💔💥 PYTHONPATH was not patched! Value: {sys.path}"
    )
    assert all(not path.startswith("/usr/local/") for path in sys.path), (
        f"💥💔💥 PYTHONPATH include system locations: {[path for path in sys.path if path.startswith('/usr/local')]}!"
    )
    assert f"{prefix}/bin" in os.environ["PATH"], (
        f"💥💔💥 PATH was not patched! Value: {os.environ['PATH']}"
    )
    assert prefix == os.environ.get("CONDA_PREFIX"), (
        f"💥💔💥 CONDA_PREFIX value: {os.environ.get('CONDA_PREFIX', '<not set>')} does not match conda installation location {prefix}!"
    )

    assert f"{pymaj}.{pymin}" == TARGET_PYTHON, (
        f"💥💔💥 Python version {pymaj}.{pymin} does not match expected value: {TARGET_PYTHON}"
    )
    assert sitepackages in sys.path, (
        f"💥💔💥 PYTHONPATH was not patched! Value: {sys.path}"
    )
    assert f"{prefix}/bin" in os.environ["PATH"], (
        f"💥💔💥 PATH was not patched! Value: {os.environ['PATH']}"
    )
    assert f"{prefix}/lib" in os.environ["LD_LIBRARY_PATH"], (
        f"💥💔💥 LD_LIBRARY_PATH was not patched! Value: {os.environ['LD_LIBRARY_PATH']}"
    )
    if verbose:
        print("✨🍰✨ Everything looks OK!")


def install_miniforge(
    prefix: str | Path = PREFIX,
    env: Dict[AnyStr, AnyStr] = None,
    pre_conda: str = None,
    run_checks: bool = True,
    restart_kernel: bool = True,
    environment_file: str = None,
    python_version: str = None,
    specs: Iterable[str] = (),
    channels: Iterable[str] = (),
    pip_args: Iterable[str] = (),
    extra_conda_args: Iterable[str] = (),
) -> None:
    """
    Install Miniforge 25.11.1, built for Python 3.12.

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
    installer_url = (
        "https://github.com/conda-forge/miniforge/releases/download/"
        "25.11.0-1/Miniforge3-25.11.0-1-Linux-x86_64.sh"
    )
    checksum = "be1bad9d4e67a8753eb76fb4940e9a08036786675c7adf060627e55791bf110d"
    install_from_url(
        installer_url,
        prefix=prefix,
        env=env,
        pre_conda=pre_conda,
        run_checks=run_checks,
        restart_kernel=restart_kernel,
        environment_file=environment_file,
        python_version=python_version,
        specs=specs,
        channels=channels,
        pip_args=pip_args,
        extra_conda_args=extra_conda_args,
        sha256=checksum,
    )


# Make miniforge the default
install = install_miniforge


def install_miniconda(*args, **kwargs):
    print(
        "This function has been deprecated. If you still need it, install condacolab==0.1",
        file=sys.stderr,
    )


install_anaconda = install_miniconda

__all__ = [
    "install_from_url",
    "install",
    "install_miniforge",
    "install_miniconda",
    "install_anaconda",
    "check",
    "PREFIX",
    "TARGET_PYTHON",
]
