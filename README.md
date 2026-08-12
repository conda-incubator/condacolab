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

## Example notebook

Check [this example notebook](https://colab.research.google.com/drive/1revmGyR9EFLg-zNj9jcAb9EA8ZHlNPtU?usp=sharing) for more information.
