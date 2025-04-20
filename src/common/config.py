import yaml
from pathlib import Path
from typing import Union
from common.paths import BASE_DIR

FILE_DIR = Path(__file__).parent.resolve()


def load_config(config_path: Union[str, Path, None], default_config: dict) -> dict:
    if config_path is None:
        config_path = FILE_DIR / "config.yaml"
    else:
        config_path = Path(config_path)
    full_path = BASE_DIR / config_path

    if not full_path.exists():
        raise FileNotFoundError(f"Config file at '{full_path}' path not found")

    with open(full_path, "r", encoding="utf-8") as f:
        try:
            file_config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML config: {e}")

    config = default_config.copy()
    config.update(file_config)
    return config
