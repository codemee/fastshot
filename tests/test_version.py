from importlib.metadata import version

from fshot import __version__


def test_runtime_version_comes_from_package_metadata():
    assert __version__ == version("fshot")
