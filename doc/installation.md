# Installation

## With pip

You can install the toolbox with pip:

```bash
pip install copernicusmarine-delivery
```

Similarly, if your environment prevents from installing with the system's pip, you can install it in a [virtual environment](https://docs.python.org/3/library/venv.html):

```bash
python -m venv .venv
source .venv/bin/activate
pip install copernicusmarine-delivery
```

Then check that the installation was successful by running:

```bash
copernicusmarine-delivery --help
```

or

```bash
cm-de --help
```

Or in your Python environment:

```python
import copernicusmarine_delivery

print(copernicusmarine_delivery.__version__)
```

## Domains required by the Copernicus Marine Delivery

To be able to use the Copernicus Marine Services, you need to be able to access those domains:

- https://auth.marine.copernicus.eu: for the authentication process.
- https://s3.lcj1-1.cloudferro.com: for uploading data to the ingestion bucket.
- https://opdv-api-dta.lobelia.earth: for the API this tool relies on.

### Test connection

To check if you are able to access you can try the `--list-deliveries` command once the tool has been installed:

```bash
copernicusmarine-delivery list-deliveries
```

If no errors shown (no deliveries does not mean error), it means that there is access to the above three addresses.

#### Python test

If you wish to specifically test the connection to ``https://opdv-api-dta.lobelia.earth`` or ``https://s3.lcj1-1.cloudferro.com``, you can do the following Python/Shell scripts.

First, open a Python console in the same environment as you would run your script:

```
python
```

Then, run a requests and check that the result is as expected:

```python
import requests

response = requests.get("https://opdv-api-dta.lobelia.earth/.well-known/config")
response.raise_for_status()

print(response.json())
```

You should see something along these lines:

```
{'oidc_config': [...], 'api_limits': {'max_number_of_files_per_delivery': 10000, 'max_delivery_size_gb': 200.0, 'max_file_size_gb': 40.0}}
```

For the ingestion buckets, try a head request to the endpoint url:

```python
import requests

response = requests.head("https://s3.lcj1-1.cloudferro.com")
response.raise_for_status()

print(response)
```

If successful, you should see something along these lines:

```
<Response [200]>
```

#### Bash test

Alternatively, if you do not wish to use Python, you can try the following in a terminal:

```bash
 curl -X GET https://opdv-api-dta.lobelia.earth/.well-known/config
```

and

```bash
curl -I https://s3.lcj1-1.cloudferro.com
```

If any of these commands does not execute successfully please contact the MDS Service Desk as they are necessary for the toolbox usage.