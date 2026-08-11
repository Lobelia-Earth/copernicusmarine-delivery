import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from pusher.environment_variables import ALLOW_HTTP

_retry_strategy = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)

_adapter = HTTPAdapter(max_retries=_retry_strategy)

http_client = requests.Session()
http_client.mount("https://", _adapter)
if ALLOW_HTTP:
    http_client.mount("http://", _adapter)
