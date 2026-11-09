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
- https://opdv-api.copernicusmarine.eu: for the API this tool relies on.
