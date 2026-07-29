import pathlib

# Namespace shim: add-on services physically live under extensions/addons/<pack>/
# but are still importable as services.<service_name>.
_services_dir = pathlib.Path(__file__).parent
_addons_root = _services_dir.parent / "extensions" / "addons"
if _addons_root.is_dir():
    for _pack_dir in _addons_root.iterdir():
        if _pack_dir.is_dir():
            _path = str(_pack_dir)
            if _path not in __path__:
                __path__.append(_path)
