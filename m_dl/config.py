from pathlib import Path
import yaml

from .log import log


def _find_config_path():
    basedirs = [
        # parent folder of the source code
        Path(__file__).absolute().parent.parent,
        # $HOME folder
        Path("~").expanduser(),
    ]
    subpaths = [
        "m-dl.yaml",
        "m-dl/config.yaml",
    ]
    for base in basedirs:
        for sub in subpaths:
            path = base / sub
            log.debug("Checking %s", path)
            if path.exists():
                return path
    return None


config = {}


def load_config(path: str | Path | None = None):
    if path is None:
        path = _find_config_path()
        if path is None:
            log.warn("Config not found")
            return {}

    log.info("Loading config from %s", path)
    with open(path, "r", encoding="utf8") as f:
        rv = yaml.safe_load(f)

    assert isinstance(rv, dict)

    # update config in-place
    config.clear()
    config.update(rv)
