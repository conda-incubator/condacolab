# condacolab

<!-- [![Downloads](https://pepy.tech/badge/condacolab/week)](https://pypi.org/project/condacolab)
[![Downloads](https://pepy.tech/badge/condacolab/month)](https://pypi.org/project/condacolab)
[![Downloads](https://pepy.tech/badge/condacolab)](https://pypi.org/project/condacolab) -->

Install Conda and friends on Google Colab, easily.

![CondaColab](https://github.com/jaimergp/condacolab/raw/main/condacolab.png)

> ⚠️ **Note**: This README refers to the development version of `condacolab`. If you are looking for the stable version, please check the [`0.1.x` branch](https://github.com/conda-incubator/condacolab/tree/0.1.x).

## Basic usage

On your Colab notebook, run the following code as the _first executable cell_:

```python
!pip install -q "https://github.com/conda-incubator/condacolab/archive/main.zip"
import condacolab
condacolab.install()
```

After the kernel restart, you can optionally add a new cell to check that everything is in place:

```python
import condacolab
condacolab.check()
```

> It is important that you perform the installation first thing in the notebook because it will require a kernel restart, thus resetting the variables set up to that point.
