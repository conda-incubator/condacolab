# How to cut a release

1. Modify versions in _both_ `pyproject.toml` and `condacolab.py`.
2. Commit.
3. Create a new tag.
4. `poetry build`.
5. `poetry publish`.
