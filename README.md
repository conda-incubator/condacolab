# condacolab

Install Conda and friends on Google Colab, easily.

![CondaColab](condacolab.png)

## Usage

> **TLDR**: Check the [example notebook here](https://colab.research.google.com/drive/1c_RGCgQeLHVXlF44LyOFjfUW32CmG6BP)!

On your Colab notebook, run the following code as the _first executable cell_:

```python
!pip install -q condacolab
import condacolab
condacolab.install()
```

After the kernel restart, you can optionally add a new cell to check that everything is in place:

```python
import condacolab
condacolab.check()
```

> It is important that you perform the installation first thing in the notebook because it will require a kernel restart, thus resetting the variables set up to that point.

The default `condacolab.install()` provides Mambaforge, but there are other `conda` distributions to choose from:

- `install_anaconda()`: This will install the Anaconda 5.2.0 distribution, the last version that was built for Python 3.6. This contains [plenty of data science packages](https://docs.anaconda.com/anaconda/packages/old-pkg-lists/5.2.0/py3.6_linux-64/), but they might be outdated by now.
- `install_miniconda()`: This will install the Miniconda 4.5.4 distribution, the last version that was built for Python 3.6. Unlike Anaconda, this distribution only contains `python` and `conda`.
- `install_miniforge()`: Like Miniconda, but built off `conda-forge` packages. The Miniforge distribution is officially provided by [conda-forge](https://github.com/conda-forge/miniforge) but I [forked and patched it](https://github.com/jaimergp/miniforge) so it's built for Python 3.6.
- `install_mambaforge()`: Like Miniforge, but with `mamba` included. The Mambaforge distribution is officially provided by [conda-forge](https://github.com/conda-forge/miniforge) but I [forked and patched it](https://github.com/jaimergp/miniforge) so it's built for Python 3.6.

For advanced users, `install_from_url()` is also available. It expects a URL pointing to a [`constructor`-like installer](https://github.com/conda/constructor), so you can prebuild a Python distribution that fulfills your own needs.

Once the installation is done, you can use `conda` and/or `mamba` to install the needed packages:

```bash
!conda install openmm

# or, faster:
!mamba install openmm
```

If you have a environment file (e.g. `environment.yml`), you can use it like this:

```bash
!conda env update -n base -f environment.yml

# or, faster:
!mamba env update -n base -f environment.yml
```

## How does it work

Google Colab runs on Python 3.6. We install the Miniconda distribution on top of the existing one at `/usr/local`, add a few configuration files so we stay with Python 3.6 (`conda` auto updates by default) and the newly installed packages are available. Finally, we wrap the Python executable to redirect and inject some environment variables needed to load the new libraries. Since we need to re-read `LD_LIBRARY_PATH`, a kernel restart is needed.

## Shortcomings

- The Python kernel needs to be restarted for changes to be applied. This happens automatically. If you are wondering why you are seeing a message saying _"Your session crashed for an unknown reason"_, this is why. You can safely ignore this message!
- You can only use the `base` environment, so do not try to create more environments with `conda create`.
