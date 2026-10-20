# Copernicus Marine Delivery documentation

```{warning}
This is a package for the **data producers** of the Copernicus Marine Service. If you need to access and download data, please use the [`copernicusmarine` package](https://toolbox-docs.marine.copernicus.eu/en/stable/).
```

```{warning}
This package is in development and may undergo significant changes.
```

The `copernicusmarine-delivery` package helps data producers upload data to the Copernicus Marine Data Store (MDS).

This package exposes both a **command line interface (CLI)** and a **Python API** to submit and get the status of data deliveries (uploads and deletes).

Once data is delivered, it will be validated and published to the MDS Data Lake, available to users.

```{toctree}
:maxdepth: 2
:caption: Contents:

quick-start
concepts
credentials
installation
command-line-interface/index
python-interface/index
error-handling
troubleshooting
faq
best-practices
roadmap
```
