# condacolab

[![Downloads](https://pepy.tech/badge/condacolab/week)](https://pypi.org/project/condacolab)
[![Downloads](https://pepy.tech/badge/condacolab/month)](https://pypi.org/project/condacolab)
[![Downloads](https://pepy.tech/badge/condacolab)](https://pypi.org/project/condacolab)

Install Conda and friends on Google Colab, easily.

![CondaColab](https://github.com/jaimergp/condacolab/raw/main/condacolab.png)

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

- `install_miniconda()`: This will install the Miniconda distribution, using a version built for Python 3.11. Unlike Anaconda, this distribution only contains `python` and `conda`.
- `install_miniforge()`: Like Miniconda, but built off `conda-forge` packages. The Miniforge distribution is officially provided by [conda-forge](https://github.com/conda-forge/miniforge).

For advanced users, `install_from_url()` is also available. It expects a URL pointing to a [`constructor`-like installer](https://github.com/conda/constructor), so you can prebuild a Python 3.11 distribution that fulfills your own needs.

> If you want to build your own `constructor`-based installer, check the FAQ below!

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


## Shortcomings

- The Python kernel needs to be restarted for changes to be applied. This happens automatically. If you are wondering why you are seeing a message saying _"Your session crashed for an unknown reason"_, this is why. You can safely ignore this message!
- You can only use the `base` environment, so do not try to create more environments with `conda create`. If you have an environment file, use `conda env update -n base -f <your-file.yml>`.

## FAQ

### How does it work?

Google Colab runs on Python 3.11. We install the Miniconda distribution on top of the existing one at `/usr/local`, add a few configuration files so we stay with Python 3.11 and the newly installed packages are available. Finally, we wrap the Python executable to redirect and inject some environment variables needed to load the new libraries. Since we need to re-read `LD_LIBRARY_PATH`, a kernel restart is needed.

### How can I cache my installation? I don't want to wait every time I start Colab.

The recommended approach is to build your own `constructor`-based installer. We have provided an example in `constructor-example/construct.yaml`.

> You can generate a `constructor` installer on Colab too! Follow [this tutorial](https://colab.research.google.com/github/jaimergp/condacolab/blob/main/constructor-example/condacolab_constructor_tutorial.ipynb).

Locally, follow these steps:

1. In your local computer:

```bash
conda create -n constructor -c conda-forge constructor
conda activate constructor
mkdir my-installer
cd my-installer
curl -sLO https://raw.githubusercontent.com/jaimergp/condacolab/main/constructor-example/construct.yaml
curl -sLO https://raw.githubusercontent.com/jaimergp/condacolab/main/constructor-example/pip-dependencies.sh
```

2. Add your `conda` packages to `construct.yaml` in the `specs` section. Read the comments to respect the constrains already present! You can also adapt the metadata to your liking.
3. If you _do_ need to install `pip` requirements, uncomment the `post_install` line and edit `pip-dependencies.sh`.
4. Run `constructor --platform linux-64 .`
5. Upload the resulting `.sh` to an online location with a permanent URL. GitHub Releases is great for this!
6. In Colab, run:

```python
!pip install -q condacolab
import condacolab
condacolab.install_from_url(URL_TO_YOUR_CUSTOM_CONSTRUCTOR_INSTALLER)
```

## Can I install R packages?

Yes, as long as you make sure you also install `rpy2` to overwrite Colab's installation.
See [issue #26](https://github.com/conda-incubator/condacolab/issues/26) for more details.
