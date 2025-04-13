from pathlib import Path
import argparse


def parse_args(default_dir: Path) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=default_dir / "config.yaml")
    return parser.parse_args()
