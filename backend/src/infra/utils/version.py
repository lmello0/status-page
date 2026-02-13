import importlib.util
from pathlib import Path


def get_version() -> str:
    default_version = "1.0.0"
    project_root = Path(__file__).parent.parent.parent.parent

    try:
        from version import __version__

        return __version__
    except ImportError:
        version_module_path = project_root / "version.py"

        if version_module_path.is_file():
            spec = importlib.util.spec_from_file_location("version", version_module_path)

            if spec is None:
                return default_version

            module = importlib.util.module_from_spec(spec)

            if spec.loader is not None:
                spec.loader.exec_module(module)

            return getattr(module, "__version__", default_version)

    return default_version
