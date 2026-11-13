import logging

from copernicusmarine_delivery.environment_variables import COPERNICUSMARINE_SERVICE_LOG_LEVEL

LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class CustomFormatter(logging.Formatter):
    _format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    def format(self, record):
        formatter = logging.Formatter(self._format, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


logHandler = logging.StreamHandler()
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

logger = logging.getLogger("copernicusmarine-delivery")
logger.setLevel(COPERNICUSMARINE_SERVICE_LOG_LEVEL)
logger.addHandler(logHandler)
