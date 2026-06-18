from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("home-cinema-control")
except PackageNotFoundError:
    __version__ = "dev"
