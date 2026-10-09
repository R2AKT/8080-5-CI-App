"""Project version and build information."""

__version__ = "2.1.7"
__build__ = "20261009"
__app_name__ = "i8080-5 CI"

def get_version_string():
    """Return formatted version string for display."""
    return f"{__app_name__} v{__version__} (build {__build__})"
