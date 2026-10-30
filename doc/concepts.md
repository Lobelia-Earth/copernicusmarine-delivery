# Concepts

## Operations

Operations are the processes you want to run through the ingestion platform.
Two types of operations are currently supported:

- **upload**: uploads local files to the ingestion system. Once validated, those files are published to the Copernicus Marine Data system and become accessible to the public and to all other services.
- **delete**: requests the deletion of files that are present in Copernicus Marine Data.

## Delivery

A delivery is a list of "uploads" and "deletes" that are **run sequentially**. If you start uploads and deletes as separate deliveries, they will be processed in parallel. A delivery forces the system to run these operations sequentially instead.

Deliveries are defined at the datasetID level, i.e. if you need to submit operations for two distinct datasets, then two deliveries must be submitted.

```{note}
When using the "upload" and "delete" functions directly, you submit a delivery of one operation.
```

### Delivery status

A delivery has one of these four statuses:

- **pending**: the delivery has been received by the ingestion system and is waiting to be validated.
- **validated**: the ingestion system has validated the delivery. It checks, among other things, that the product and dataset IDs are valid, that the delivery is within the [limits](best-practices.md#delivery-limits), that the uploaded files are in the ingestion system with the expected checksum, and that the files to delete exist in the MDS. The files have not reached the MDS yet.
- **completed**: the files have reached their destination in the MDS.
- **failed**: something went wrong along the way, for example the validation did not pass.

`completed` and `failed` are the final statuses. A delivery goes from `pending` to `validated` to `completed`, or to `failed` at any point.

```{note}
If only some of the operations of a delivery fail, the delivery is still `completed`. The status then comes with an error message, and the error of each file can be seen with `--show-all` in the [status command](command-line-interface/usage.md#delivery-status-command). In Python, the error message is the `error_message` of the object returned by `delivery_status`.
```

## Folder structure and path

Let's define the different paths you can encounter:

- **Relative local path**: path to a file present in the system relative to the working directory.
- **Absolute local path**: absolute path to a file present in the system.
- **S3 MDS path**: S3 key of the file published in MDS buckets. Usually in the form: `productID/datasetID/some/folders/filename.nc`
- **S3 MDS suffix**: the S3 key suffix of the file, the part that is decided by the producers. From the example above it would be: `some/folders/filename.nc`.

Right now, the ingestion system (OPDV) only accepts **S3 MDS suffixes**.

Right now, `copernicusmarine-delivery` accepts the following:

- For the **upload**, you can specify an `anchor` (which can differ per operation) together with the list of file paths. The `anchor` is optional. The file path can then be:
  - a **relative local path** without `anchor`, in which case **the file will be published with the same folder structure.** For example, if the source is `my/local/folder/filename.nc`, then in MDS the file will be published with the key: `productID/datasetID/my/local/folder/filename.nc`.
  - a **relative local path** with `anchor`, in which case **the file will be published with the same folder structure AFTER the anchor**. For example, if the source is `my/local/folder/filename.nc` and the anchor is `local`, then in MDS the file will be published with the key: `productID/datasetID/folder/filename.nc`.
  - an **absolute path** without `anchor`. The system will turn the absolute path into a relative one, local to where it is being executed, and remove any `../`. This is not recommended.
  - an **absolute path** with `anchor`. This behaves the same as a relative local path with an anchor, and **the file will be published with the same folder structure AFTER the anchor**.

It is **highly recommended** to use either relative local paths that match the folder structure (suffix) in S3 MDS, or an `anchor`, to prevent leaking the local folder structure to S3.

- For the **delete**, you have to pass the **S3 MDS suffix** (i.e. without datasetID and productID). For example, `some/folders/filename.nc` would work, whereas `filename.nc` and `productID/datasetID/some/folders/filename.nc` would not.

Whatever the input, all output paths from the toolbox will be S3 MDS suffixes for the OPDV to ingest.

```{note}
The fact that OPDV takes S3 MDS suffixes as input is an internal detail.
However, what the toolbox accepts as input can be changed.
We want to add a way to pass a local path and an S3 MDS structure at some point.
If you have any suggestions about this, don't hesitate to share.
```

### Using The Anchor

The local path of a file is not always the path you want in the MDS. The `anchor` tells the tool **which folder of the local path is the "root" of your dataset**. Everything up to and including the anchor is dropped; everything after it is kept as the S3 MDS suffix.

```text
local path:     /data/my_project/run_42/dataset1/2024/01/file.nc
anchor:         dataset1
                └────────── dropped ───────────┘└──── kept ────┘
S3 MDS suffix:  2024/01/file.nc
S3 MDS key:     productID/datasetID/2024/01/file.nc
```

Think of the anchor as a marker you stick in the path: "my dataset starts right after this folder".

Rules:

- The anchor is a **folder name**, not a partial path or a pattern. It must match a full folder name of the path (`local` matches `my/local/folder`, but not `my/localhost/folder`).
- It must be present in the path of **every file of the operation**. Otherwise, the delivery is rejected with `Expected anchor (...) was not found in local path`.
- If the folder name appears more than once in a path, the **first** occurrence is used.
- The anchor is set **per upload operation**: different operations of the same delivery can use different anchors.
- The anchor is only used by **upload**. For delete, you pass the S3 MDS suffix directly.
- Without anchor, the full relative path is kept. Absolute paths are rejected.

More examples:

```text
# relative path, no anchor: the whole path is kept
local path:     dataset1/2024/file.nc
s3 mds suffix:  dataset1/2024/file.nc

# relative path, anchor
local path:     my/local/folder/filename.nc
anchor:         local
s3 mds suffix:  folder/filename.nc

# absolute path, anchor: the part before the anchor (the machine-specific part) is gone
local path:     /home/me/exports/dataset1/file.nc
anchor:         dataset1
s3 mds suffix:  file.nc

# the same anchor can serve files in different subfolders
local paths:    /data/dataset1/2024/a.nc  and  /data/dataset1/2025/b.nc
anchor:         dataset1
s3 mds suffixes: 2024/a.nc  and  2025/b.nc
```

### Delivery file (YAML)

The `delivery` command takes a YAML file describing the operations to run, in order.

Schema:

```yaml
delivery:                      # required. List of operations, run in order
  - operation: <operation>     # required. "upload" | "delete"
    files: [<string>, ...]     # required. Local paths (upload) or S3 MDS suffixes (delete)
    anchor: <string>           # optional. upload only. Folder name in the local paths
```

Example:

```yaml
delivery:
  - operation: delete
    files:
      - 2024/01/old.nc
  - operation: upload
    anchor: dataset1
    files:
      - /data/dataset1/2024/01/file.nc
```

| Field | Required | Applies to | Description |
| --- | --- | --- | --- |
| `delivery` | yes | | List of operations. They run in the order they are written. |
| `operation` | yes | | `upload` or `delete`. |
| `files` | yes | both | For `upload`, local file paths (relative or absolute). For `delete`, [S3 MDS suffixes](#folder-structure-and-path). |
| `anchor` | no | `upload` | Folder name that marks where the S3 MDS suffix starts. See [using the anchor](#using-the-anchor). |

The product and the dataset are not part of the file: they are passed with `--product-id` and `--dataset-id`, which is why a delivery file is always for one dataset.

The YAML file is only needed for the command line. With the Python interface you don't write any file: the delivery is built in memory by the `Delivery` object, from the `Upload` and `Delete` operations you pass to it. `Upload` has the `anchor` argument, and the operations run in list order.

The same delivery in Python:

```python
from copernicusmarine_delivery import Delivery, Upload, Delete

Delivery(
    operations=[
        Delete(files=["2024/01/old.nc"]),
        Upload(files=["/data/dataset1/2024/01/file.nc"], anchor="dataset1"),
    ]
)
```
