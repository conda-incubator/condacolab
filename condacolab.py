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
from distutils.spawn import find_executable
from pathlib import Path
from subprocess import check_output, run, PIPE, STDOUT
from textwrap import dedent
from typing import Dict, AnyStr, Iterable
from urllib.request import urlopen
from urllib.error import HTTPError

from IPython.display import display
from IPython import get_ipython

try:
    from ruamel.yaml import YAML
    from ruamel.yaml.comments import CommentedMap
except ImportError as e:
    raise RuntimeError("Could not find ruamel.yaml, plese install using `!pip install ruamel.yaml`!") from e

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

yaml=YAML()

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


def _update_environment(
    prefix:os.PathLike = PREFIX,
    environment_file: str = None,
    python_version: str = None,
    specs: Iterable[str] = (),
    channels: Iterable[str] = (),
    pip_args: Iterable[str] = (),
    extra_conda_args: Iterable[str] = (),
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

        with open(environment_file_path, 'w') as f:
            yaml.indent(mapping=2, sequence=4, offset=2)
            yaml.dump(env_details, f)
    else:
        # If URL is given for environment.yaml file
        if environment_file.startswith(("http://", "https://")):
            try:
                with urlopen(environment_file) as response, open(environment_file_path, "wb") as out:
                    shutil.copyfileobj(response, out)
            except HTTPError as e:
                raise HTTPError("The URL you entered is not working, please check it again.") from e

        # If path is given for environment.yaml file
        else:
            shutil.copy(environment_file, environment_file_path)

        with open(environment_file_path, 'r') as f:
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

        with open(environment_file_path, 'w') as f:
            f.truncate(0)
            yaml.dump(env_details, f)

    _run_subprocess(
        [f"{prefix}/bin/python", "-m", "conda_env", "update", "-n", "base", "-f", environment_file_path, *extra_conda_args],
        "environment_file_update.log",
    )


def install_from_url(
    installer_url: AnyStr,
    prefix: os.PathLike = PREFIX,
    env: Dict[AnyStr, AnyStr] = None,
    run_checks: bool = True,
    restart_kernel: bool = True,
    environment_file: str = None,
    python_version: str = None,
    specs: Iterable[str] = (),
    channels: Iterable[str] = (),
    pip_args: Iterable[str] = (),
    extra_conda_args: Iterable[str] = (),
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

    _update_environment(
        prefix=prefix,
        environment_file=environment_file,
        specs=specs,
        channels=channels,
        python_version=python_version,
        pip_args=pip_args,
        extra_conda_args=extra_conda_args,
        )

    env = env or {}
    bin_path = f"{prefix}/bin"

    if os.path.exists(sys.executable):
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


def install_mambaforge(
    prefix: os.PathLike = PREFIX,
    env: Dict[AnyStr, AnyStr] = None,
    run_checks: bool = True,
    restart_kernel: bool = True,
    specs: Iterable[str] = (),
    python_version: str = None,
    channels: Iterable[str] = (),
    environment_file: str = None,
    extra_conda_args: Iterable[str] = (),
    pip_args: Iterable[str] = (),

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
    restart_kernel
        Variable to manage the kernel restart during the installation
        of condacolab. Set it `False` to stop the kernel from restarting
        automatically and get a button instead to do it.
    """
    installer_url = r"https://github.com/jaimergp/miniforge/releases/latest/download/Mambaforge-colab-Linux-x86_64.sh"
    install_from_url(
        installer_url,
        prefix=prefix, 
        env=env,
        run_checks=run_checks,
        restart_kernel=restart_kernel,
        specs=specs,
        python_version=python_version,
        channels=channels,
        environment_file=environment_file,
        extra_conda_args=extra_conda_args,
        pip_args=pip_args,
        )

# Make mambaforge the default
install = install_mambaforge


def install_miniforge(
    prefix: os.PathLike = PREFIX,
    env: Dict[AnyStr, AnyStr] = None,
    run_checks: bool = True,
    restart_kernel: bool = True,
    specs: Iterable[str] = (),
    python_version: str = None,
    channels: Iterable[str] = (),
    environment_file: str = None,
    extra_conda_args: Iterable[str] = (),
    pip_args: Iterable[str] = (),
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
    install_from_url(
        installer_url,
        prefix=prefix,
        env=env,
        run_checks=run_checks,
        restart_kernel=restart_kernel,
        specs=specs,
        python_version=python_version,
        channels=channels,
        environment_file=environment_file,
        extra_conda_args=extra_conda_args,
        pip_args=pip_args,
        )


def install_miniconda(
    prefix: os.PathLike = PREFIX,
    env: Dict[AnyStr, AnyStr] = None,
    run_checks: bool = True,
    restart_kernel: bool = True,
    specs: Iterable[str] = (),
    python_version: str = None,
    channels: Iterable[str] = (),
    environment_file: str = None,
    extra_conda_args: Iterable[str] = (),
    pip_args: Iterable[str] = (),
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
    install_from_url(
        installer_url,
        prefix=prefix,
        env=env,
        run_checks=run_checks,
        restart_kernel=restart_kernel,
        specs=specs,
        python_version=python_version,
        channels=channels,
        environment_file=environment_file,
        extra_conda_args=extra_conda_args,
        pip_args=pip_args,
    )


def install_anaconda(
    prefix: os.PathLike = PREFIX,
    env: Dict[AnyStr, AnyStr] = None,
    run_checks: bool = True,
    restart_kernel: bool = True,
    specs: Iterable[str] = (),
    python_version: str = None,
    channels: Iterable[str] = (),
    environment_file: str = None,
    extra_conda_args: Iterable[str] = (),
    pip_args: Iterable[str] = (),
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
    install_from_url(        
        installer_url,
        prefix=prefix,
        env=env,
        run_checks=run_checks,
        restart_kernel=restart_kernel,
        specs=specs,
        python_version=python_version,
        channels=channels,
        environment_file=environment_file,
        extra_conda_args=extra_conda_args,
        pip_args=pip_args,
    )


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
    "install_mambaforge",
    "install_miniforge",
    "install_miniconda",
    "install_anaconda",
    "check",
    "PREFIX",
]
