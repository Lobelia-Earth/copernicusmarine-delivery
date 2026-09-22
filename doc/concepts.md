# Concepts

## Operations

Operations are the processes you want to run through the ingestion platform.
Two types of operations are supported right now:

- **upload**: uploads the local files to the ingestion system. Once validated, those files are published to the Copernicus Marine Data system and will be accessible by the public and all the other services.
- **delete**: requests deletion of files that are present in Copernicus Marine Data.

## Delivery

A delivery is a list of "uploads" and "deletes" that are **run sequentially**. If you start uploads and deletes as separate deliveries, they will be processed in parallel. A delivery forces the system to run these operations sequentially instead.

Deliveries are defined at the datasetID level, i.e. if you need to submit operations for two distinct datasets, then two deliveries need to be submitted.

```{note}
When using the "upload" and "delete" functions directly, you submit a delivery of one operation.
```

## Folder structure and path

Let's define the different paths you can encounter:

- **Relative local path**: path to a file present in the system relative to the working directory.
- **Absolute local path**: absolute path to a file present in the system.
- **S3 MDS path**: S3 key of the file published in MDS buckets. Usually in the form: `productID/datasetID/some/folders/filename.nc`
- **S3 MDS suffix**: the S3 key suffix of the file, the part that is decided by the producers. From the example above it would be: `some/folders/filename.nc`.

Right now, the ingestion system (OPDV) only accepts **S3 MDS suffixes**.

Right now, `copernicusmarine-delivery` accepts the following:

- For the **upload**, you can specify an `anchor` (which can be different per operation) together with the list of file paths. The `anchor` is optional. Then the file path can be:
  - a **relative local path** without `anchor` and **the file will be published with the same folder structure.** For example, if the source is `my/local/folder/filename.nc`, then in MDS the file will be published with the key: `productID/datasetID/my/local/folder/filename.nc`.
  - a **relative local path** with `anchor`, **the file will be published with the same folder structure AFTER the anchor**. For example, if the source is `my/local/folder/filename.nc` and the anchor is `local`, then in MDS the file will be published with the key: `productID/datasetID/folder/filename.nc`.
  - an **absolute path** without `anchor`. The system will make the absolute path a relative one, local to where it's being executed and remove any `../`. This is not recommended.
  - an **absolute path** with `anchor`. This will have the same behaviour as a relative local path with anchor and **the file will be published with the same folder structure AFTER the anchor**.

It is **highly recommended** to use either relative local paths that match the folder structure (suffix) in S3 MDS, or the usage of `anchor` to prevent leaking local folder structure to S3.

- For the **delete**, you have to pass the **S3 MDS suffix** (i.e. without datasetID and productID). For example, `some/folders/filename.nc` would work. `filename.nc` and `productID/datasetID/some/folders/filename.nc` would not work.

Whatever the input, all output paths from the toolbox will be S3 MDS suffixes for the OPDV to ingest.

```{note}
The fact that OPDV takes S3 MDS suffixes as input is an internal detail. However, what the toolbox accepts as input can be changed. We want to add a way to pass a local path and an S3 MDS structure at some point. If you have any suggestions about this, don't hesitate to share.
```
