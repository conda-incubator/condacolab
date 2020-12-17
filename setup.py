"""
CondaColab
Install Conda and friends on Google Colab, easily
"""
import sys
from setuptools import setup, find_packages

short_description = __doc__.split("\n")

try:
    with open("README.md", "r") as handle:
        long_description = handle.read()
except:
    long_description = "\n".join(short_description[2:])


setup(
    # Self-descriptive entries which should always be present
    name="condacolab",
    author="Jaime Rodríguez-Guerra",
    author_email="jaime.rogue@gmail.com",
    description=short_description[0],
    long_description=long_description,
    long_description_content_type="text/markdown",
    version="0.0.1",
    license="MIT",
    py_modules=["condacolab"],
    include_package_data=True,
    url="http://github.com/jaimergp/condacolab",  # Website
    platforms=["Linux"],
    python_requires=">=3.6",  # Python version restrictions
)