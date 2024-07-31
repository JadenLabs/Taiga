import os
from dotenv import load_dotenv
from src.utils import Env, logger, Config, get_args


class Core:
    """Initialize the bot's setup.
    Check if the config, env, and other required values are valid.
    """

    def __init__(self, env: Env, config_file: str = "config.toml"):
        # Env
        self.env = env
        logger.debug(f"Using env: {self.env.name}")
        self.get_env(self.env)

        # Config
        self.config_file = config_file
        logger.debug(f"Using config: {self.config_file}")
        self.config = Config(config_file)

    def get_env(self, env: Env):
        logger.debug(f"Getting env: {env.name}")

        # Check if env file exits - if not: exit
        env_exists = os.path.exists(env.env_path)
        if not env_exists:
            logger.critical(f"The `{env.name}` env file does not exist")
            envs = self.get_envs()
            envs_str = [env.env_path for env in envs]
            logger.debug(f"Other available envs: {envs_str}")
            exit(0)

        # Load dotenv
        load_dotenv(env.env_path)

        # Validate env
        BOT_TOKEN = os.getenv("BOT_TOKEN")
        assert BOT_TOKEN, f"The BOT_TOKEN value in `{env.env_path}` is not set"
        logger.debug(f"Checked `BOT_TOKEN`, value present")


try:
    args = get_args()
    env = Env(args.env)
    core = Core(env=env, config_file=args.config)
except AssertionError as e:
    logger.error(f"{e}")
