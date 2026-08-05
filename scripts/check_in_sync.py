#!/usr/bin/env python
"""
Verify that __version__ and TARGET_PYTHON in condacolab.py match
the fields version and python-requires in pyproject.toml, respectively.
"""

import re
import sys
from pathlib import Path


def main():
    root_dir = Path(__file__).parent.parent    
    condacolab_file = root_dir / "condacolab.py"
    condacolab_content = condacolab_file.read_text()
    
    # Extract __version__ and TARGET_PYTHON from condacolab.py
    version_match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', condacolab_content)
    target_python_match = re.search(r'TARGET_PYTHON\s*=\s*["\']([^"\']+)["\']', condacolab_content)
    
    if not version_match:
        print("❌ ERROR: Could not find __version__ in condacolab.py")
        return False
    if not target_python_match:
        print("❌ ERROR: Could not find TARGET_PYTHON in condacolab.py")
        return False
    
    condacolab_version = version_match.group(1)
    condacolab_target_python = target_python_match.group(1)
    
    # Read pyproject.toml
    pyproject_file = root_dir / "pyproject.toml"
    pyproject_content = pyproject_file.read_text()
    
    # Extract version and python-requires from pyproject.toml
    version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', pyproject_content)
    requires_python_match = re.search(r'requires-python\s*=\s*["\']==([0-9a-z\.]+)\.\*["\']', pyproject_content)
    
    if not version_match:
        print("❌ ERROR: Could not find version in pyproject.toml")
        return False
    if not requires_python_match:
        print("❌ ERROR: Could not find requires-python in pyproject.toml")
        return False
    
    pyproject_version = version_match.group(1)
    pyproject_requires_python = requires_python_match.group(1)
    
    # Compare values
    all_match = True
    
    if condacolab_version != pyproject_version:
        print("❌ ERROR: Version mismatch!")
        print(f"  condacolab.py __version__: {condacolab_version}")
        print(f"  pyproject.toml version: {pyproject_version}")
        all_match = False
    else:
        print(f"✅ Versions match: {condacolab_version}")
    
    if condacolab_target_python != pyproject_requires_python:
        print("❌ ERROR: Python requirement mismatch!")
        print(f"  condacolab.py TARGET_PYTHON: {condacolab_target_python}")
        print(f"  pyproject.toml python-requires: {pyproject_requires_python}")
        all_match = False
    else:
        print(f"✅ Required Python matches: {condacolab_target_python}")
    
    return all_match


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
