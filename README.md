# condacolab

<!-- [![Downloads](https://pepy.tech/badge/condacolab/week)](https://pypi.org/project/condacolab)
[![Downloads](https://pepy.tech/badge/condacolab/month)](https://pypi.org/project/condacolab)
[![Downloads](https://pepy.tech/badge/condacolab)](https://pypi.org/project/condacolab) -->

Install conda packages on Google Colab, easily.

![CondaColab](https://github.com/jaimergp/condacolab/raw/main/condacolab.png)

> ⚠️ **Note**: This README refers to the development version of `condacolab`. If you are looking for the stable version, please check the [`0.1.x` branch](https://github.com/conda-incubator/condacolab/tree/0.1.x).

## Basic usage

On your Colab notebook, run the following code as the _first executable cell_:

```python
!pip install -q "https://github.com/conda-incubator/condacolab/archive/main.zip"
import condacolab
condacolab.install()
```

> It is important that you perform the installation first thing in the notebook because it will require a kernel restart, thus resetting the variables set up to that point.

This will set up a bare environment with only the essentials to run the Python kernel. If you need
more packages, use the `dependencies` and/or `pypi_dependencies` arguments. You can also change
the default Python version.

```python
# Use Python 3.14
condacolab.install(python_version="3.14")
# Install numpy>=2 and scipy
condacolab.install(dependencies={"numpy": ">=2", "scipy": "*"})
```

## FAQ

### Do you have any examples to get started?

Yes, check [this example notebook](https://colab.research.google.com/drive/1revmGyR9EFLg-zNj9jcAb9EA8ZHlNPtU?usp=sharing) for more information.

### How can I use my `environment.yml` with `condacolab`?

`condacolab` or Pixi do no support them directly, but here's a one-liner workaround you can run once `condacolab.install()` has run:

```
!pixi exec conda install --file environment.yml --prefix "$CONDA_PREFIX" --yes
```

The trick is to know that the restarted kernel runs on an activated conda environment, so you can use `$CONDA_PREFIX` to refer to it. Do note that any other `pixi` operations on the environment might undo that operation, so make sure to run this workaround as the last step of the setup.
