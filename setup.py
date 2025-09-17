import tomllib
from setuptools import setup

with open("pyproject.toml", "rb") as f:
    config = tomllib.load(f)

blender_version = config["tool"]["blender"]["version"]
setup(install_requires=[f"bpy=={blender_version}"])
