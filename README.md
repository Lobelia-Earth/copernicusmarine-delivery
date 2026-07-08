# Copernicus Marine Producers Toolbox

Python library to help you upload data to the MDS.

## Installation

TODO

## Setup

You need to set the following environment variables:

- `OPDV_S3_ENDPOINT`: the URL of the OPDV S3 service.
- `OPDV_ACCESS_KEY_ID`: the access key ID to access the OPDV S3 service.
- `OPDV_SECRET_ACCESS_KEY`: the secret access key to access the OPDV S3 service.

## Concepts

### Operations

Operations are the processes you want to run through the ingestion platform.
Two types of operations are supported right now:

- "upload": uploads the local files to the ingestion system. Once validated, those files are published to the Copernicus Marine Data system and will be accessible by the public and all the other services.
- "delete": requests deletion of files that are present in Copernicus Marine Data.

### Delivery

A delivery is a list of "uploads" and "deletes" that are **run sequentially**. Indeed, if you start uploads and deletes in parallel, they will be processed in parallel. Here, a delivery forces the system to run these operations sequentially.

Deliveries are defined at datasetID level, i.e. if you need to submit operations for two distinct datasets, then two deliveries need to be submitted.

Note: when using the "upload" and "delete" functions directly, you submit a delivery of one operation.

### Folder structure and path

Let's define the different paths you can encounter:

- relative local path: path to a file present in the system relative to the working directory.
- absolute local path: absolute path to a file present in the system.
- s3 mds path: s3 key of the file published in MDS buckets. Usually in the form: `productID/datasetID/some/folders/filename.nc`
- s3 mds suffix: the s3 key suffix of the file, the part that is decided by the producers. From the example above it would be: `some/folders/filename.nc`.

Right now, the ingestion system (OPDV) only accepts **s3 mds suffixes**.

Right now, the toolbox accepts the following:

- For the "upload", you have to pass a **relative local path** and **the file will be published with the same folder structure.** For example, if the source is `my/local/folder/filename.nc`, then in MDS the file will be published with the key: `productID/datasetID/my/local/folder/filename.nc`.

- For the "delete", you have to pass the **s3 mds suffix** (i.e. without datasetID and productID). For example, `some/folders/filename.nc` would work. `filename.nc` and `productID/datasetID/some/folders/filename.nc` would not work.

> For internal testers: the fact that OPDV takes s3 mds suffixes as input is an internal detail. However, what the Toolbox accepts as input can be changed. We want to add a way to pass a local path and an s3 mds structure at some point. If you have any suggestions about this, don't hesitate to share.

## Python Interface

The Python interface is designed so that you can build your delivery step by step and then submit it.

Here are some examples for simple upload and delete:

```python
from pusher import Upload, Delete

pushing_entity_id = "some-pushing-entity-id"
product_id = "some-product-id"
dataset_id = "some-dataset-id"

# --- Delete ---
delete = Delete(["some/file.nc", "some/other/file.nc"])

# --- Upload ---
upload = Upload(["some/file.nc", "some/other/file.nc"])

# --- Add files to upload or delete ---
delete.add("another/file.nc")
upload.add("another/file.nc")

# --- submit ---
delete.submit(pushing_entity_id, product_id, dataset_id)
upload.submit(pushing_entity_id, product_id, dataset_id)
```

And here are some examples for complex deliveries:

```python
from pusher import Upload, Delete, Delivery

pushing_entity_id = "some-pushing-entity-id"
product_id = "some-product-id"
dataset_id = "some-dataset-id"

# Operations are executed in order
delivery = Delivery([
    Delete(["some/file.nc"]),
    Upload(["some/file.nc"]),
])

delivery.upload(["some/other/file.nc"])
delivery.add(Delete(["some/other/file.nc"]))

# --- submit ---
delivery.submit(pushing_entity_id, product_id, dataset_id)
```

You can then check the status of your delivery with the delivery ID:

```python
from pusher import delivery_status

manifest = delivery_status(delivery_id, pushing_entity_id, product_id, dataset_id)
```

## CLI

### Upload command

Submit a delivery for one upload operation.

See the help for the inputs:

``` bash
pusher upload --help
```

You can pass multiple sources:

``` bash
pusher upload --source some/file.nc --source some/other/file.nc --dataset-id hello --product-id world --pushing-entity-id lololo
```

> WARNING: the path for the files should be relative. It should point to a local file.
> The folder structure will also be reproduced when published.

### Delete command

Submit a delivery for one delete operation.

See the help for the inputs:

``` bash
pusher delete --help
```

You can pass multiple sources:

``` bash
pusher delete --source some/file.nc --source some/other/file.nc --dataset-id hello --product-id world --pushing-entity-id lololo
```

> WARNING: the path for the files should be the path without productID and datasetID. See the concept of folder structure and path.

### Delivery command

Submit a delivery with possibly multiple operations based on a YAML file.

See the help for the inputs:

``` bash
pusher delivery --help
```

You can pass multiple sources:

``` bash
pusher delivery --file delivery_file.yaml --dataset-id hello --product-id world --pushing-entity-id lololo
```

The delivery file should be a YAML file with the following structure:

``` yaml
delivery:
  - delete:
      - some/file.nc
      - some/other/file.nc
  - upload:
      - some/file.nc    
      - some/other/file.nc
```

### Delivery status command (WIP)

> WIP: for internal testing for the moment. Don't hesitate to suggest what this command should do.

Given the delivery ID, prints the manifest fetched from OPDV.

``` bash
pusher delivery-status --help
```

Example:

``` bash
pusher delivery-status --delivery-id some-delivery-id --dataset-id hello --product-id world --pushing-entity-id lololo
```

## Error handling

> The error handling right now might be inconsistent across the package. Please report any inconsistency.
> For example, sometimes we return a fatal error in a response object, sometimes we raise an exception.

## Features to come

Here is a list of features we intend to implement in the near future:

- Pass a folder instead of a list of files for the upload.
- Pass a glob pattern for the upload.
- Define the published S3 path of the data while pointing to a local file with a different folder structure.
- Dry-run.
- Batching: divide the upload into several smaller ones.
- Retry/rerun system: if an upload fails, you can rerun the delivery and only the failed operations will be rerun and only the failed uploads will be retried.
- Work on error consistency and documentation.
- A setup command to set the environment variables and pushing entity ID and check that they are correct.
