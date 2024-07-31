import toml
from src.utils import logger


class Config:
    def __init__(self, config_file: str = "config.toml"):
        self.config_file = config_file
        self.load_config()

    def load_config(self):
        logger.debug(f"Loading config: `{self.config_file}`")
        with open(self.config_file, "r", encoding="utf-8") as f:
            self.data = toml.load(f)
