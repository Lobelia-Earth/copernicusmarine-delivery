# Copernicusmarine Delivery package

```{warning}
This is a package for the **data producers** of the Copernicus Marine Service. If you need to access and download data, please use the [`copernicusmarine` package](https://toolbox-docs.marine.copernicus.eu/en/stable/).
```

```{warning}
This package is in development and may undergo significant changes.
```

Python library to help you upload data to the Copernicus Marine ingestion platform. After uploading your data to the ingestion system, the data will be validated and pushed to the Copernicus Marine Data Store.

This package exposes both a **command line interface (CLI)** and a **Python API** to
submit deliveries (uploads and deletes) to the ingestion platform.

```{toctree}
:maxdepth: 2
:caption: Contents:

installation
concepts
python-interface
command-line-interface
error-handling
roadmap
```

## Setup

You need to set the following environment variables:

- `COPERNICUSMARINE_USERNAME`: your Copernicus Marine username.
- `COPERNICUSMARINE_PASSWORD`: your Copernicus Marine password.
