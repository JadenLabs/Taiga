import logging
from colorlog import ColoredFormatter

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Console handler
c_handler = logging.StreamHandler()
c_handler.setLevel(logging.DEBUG)
formatter = ColoredFormatter(
    "%(log_color)s[%(levelname)s]%(reset)s %(filename)s >> %(message)s",
    log_colors={
        "DEBUG": "blue",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red",
    },
    reset=True,
    style="%",
)
c_handler.setFormatter(formatter)
logger.addHandler(c_handler)

# File handler
f_handler = logging.FileHandler("./logs/file.log")
f_handler.setLevel(logging.ERROR)
f_format = logging.Formatter("%(asctime)s | %(levelname)s | %(filename)s | %(message)s")
f_handler.setFormatter(f_format)
logger.addHandler(f_handler)
