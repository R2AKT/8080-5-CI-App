"""
Library tool for i8080-5 CI.

Packs multiple object files (.obj, format i8080-obj-v1) into a single
archive library (.lib).

Archive format: JSON-based, version 1 (i8080-lib-v1).
{
  "format": "i8080-lib-v1",
  "name": library_name,
  "index": { "EXPORT_SYMBOL": "module_name_where_declared" },
  "modules": { "module_name": { /* full object file JSON */ } }
}

The index maps UPPER-cased export symbols to the archive module that
defines them, so the linker can pull only the modules it needs.
"""
import json
import os


LIB_FORMAT_VERSION = "i8080-lib-v1"
OBJ_FORMAT_VERSION = "i8080-obj-v1"


def create_library(obj_file_paths: list[str], lib_output_path: str, lib_name: str) -> None:
    """Pack object files into an archive library (.lib).

    Args:
        obj_file_paths: Paths to object files (.obj, i8080-obj-v1).
        lib_output_path: Path of the resulting .lib archive.
        lib_name: Logical name of the library.

    Raises:
        FileNotFoundError: if an object file does not exist.
        ValueError: on unsupported format, empty or duplicate module name,
            or duplicate export symbol across modules.
    """
    index = {}    # {UPPER export symbol: module name}
    modules = {}  # {module name: full object file JSON}

    for obj_path in obj_file_paths:
        if not os.path.exists(obj_path):
            raise FileNotFoundError(f"Object file not found: {obj_path}")

        with open(obj_path, 'r', encoding='utf-8') as f:
            obj = json.load(f)

        if obj.get("format") != OBJ_FORMAT_VERSION:
            raise ValueError(
                f"Unsupported object format in {obj_path}: {obj.get('format')}")

        mod_name = obj.get("name", "")
        if not mod_name:
            raise ValueError(f"Object file {obj_path} has an empty module name")
        if mod_name in modules:
            raise ValueError(f"Duplicate module name '{mod_name}' in library")

        modules[mod_name] = obj

        for sym in obj.get("exports", []):
            key = sym.upper()
            if key in index:
                raise ValueError(
                    f"Duplicate export symbol '{sym}' in library modules")
            index[key] = mod_name

    lib = {
        "format": LIB_FORMAT_VERSION,
        "name": lib_name,
        "index": index,
        "modules": modules,
    }

    out_dir = os.path.dirname(os.path.abspath(lib_output_path))
    os.makedirs(out_dir, exist_ok=True)
    with open(lib_output_path, 'w', encoding='utf-8') as f:
        json.dump(lib, f, indent=2)


def load_library(path: str) -> dict:
    """Load an archive library from disk (.lib, i8080-lib-v1).

    Raises:
        ValueError: if the file is not a valid i8080-lib-v1 archive.
    """
    with open(path, 'r', encoding='utf-8') as f:
        lib = json.load(f)
    if lib.get("format") != LIB_FORMAT_VERSION:
        raise ValueError(f"Unsupported library format: {lib.get('format')}")
    return lib
