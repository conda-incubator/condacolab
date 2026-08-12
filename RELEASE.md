# How to cut a release

1. Modify versions in _both_ `pyproject.toml` and `condacolab.py`.
2. Open new PR with title "Mint new version: X.Y.Z"
3. Merge and publish new Release from Github with tag vX.Y.Z.
4. Github Actions will take care of the rest
