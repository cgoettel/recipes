"""recipes.skalchemy.com: the public site over the recipes repo."""

try:
    from recipes_site._version import __version__
except ImportError:  # a checkout without the build-time version file
    __version__ = "0.0.0+dev"

__all__ = ["__version__"]
