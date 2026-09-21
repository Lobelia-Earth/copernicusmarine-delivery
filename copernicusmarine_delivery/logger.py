import logging
import os


class CustomFormatter(logging.Formatter):
    _format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    def format(self, record):
        formatter = logging.Formatter(self._format, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


if os.getenv("PYTHON_LOG_DEBUG", "").lower() in ("1", "true", "yes"):
    level = logging.DEBUG
else:
    level = logging.INFO

logging.getLogger().setLevel(level)
logHandler = logging.StreamHandler()
logHandler.setLevel(level)
logHandler.setFormatter(CustomFormatter())

for _name in (
    "asyncio",
    "botocore",
    "boto3",
    "aiobotocore",
    "urllib3",
    "procrastinate",
    "aiohttp",
):
    logging.getLogger(_name).setLevel(logging.WARNING)

logger = logging.getLogger("marine-producer-toolbox")
logger.addHandler(logHandler)
