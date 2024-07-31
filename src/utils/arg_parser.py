import argparse


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-e", "--env", default=".env", type=str, help="The env file to use"
    )
    parser.add_argument(
        "-c", "--config", default="config.toml", type=str, help="The config file to use"
    )

    return parser.parse_args()
