# CLI reference

```{note}
`cm-de` is an alias of `copernicusmarine-delivery`.
```

## Synopsis

```text
copernicusmarine-delivery COMMAND [OPTIONS]
```

Commands: [`upload`](#upload), [`delete`](#delete), [`delivery`](#delivery), [`status`](#status), [`list-deliveries`](#list-deliveries).

Use `copernicusmarine-delivery COMMAND --help` to print the help of a command.

## Environment variables

`COPERNICUSMARINE_SERVICE_USERNAME`
: Username of your Pushing Entity account. Required. See [credentials](../credentials.md).

`COPERNICUSMARINE_SERVICE_PASSWORD`
: Password of your Pushing Entity account. Required.

`PYTHON_LOG_DEBUG`
: Set it to `1`, `true` or `yes` to print debug logs.

## Exit status

`0`
: Success.

`1`
: The command failed. The error is logged.

## upload

Upload local files to a dataset. It submits a delivery with one upload operation.

```text
copernicusmarine-delivery upload --product-id PRODUCT_ID --dataset-id DATASET_ID --source FILE [--source FILE ...] [OPTIONS]
```

`--source TEXT`
: Path to a local file. Relative or absolute. Can be repeated. Required. If `--anchor` is set, anything before it is removed. See [folder structure and path](../concepts.md#folder-structure-and-path).

`--anchor TEXT`
: Folder name in the path of the files. Anything before it, and the anchor itself, is removed when building the S3 MDS suffix. It must be present in all the sources. See [using the anchor](../concepts.md#using-the-anchor).

`--product-id TEXT`
: ID of the product. Required.

`--dataset-id TEXT`
: ID of the dataset. Required.

`--dry-run`
: Validate the upload without uploading or submitting anything.

`--save-delivery-json`
: Write the delivery document to `<delivery_id>.json`. It can be used later with [`status`](#status).

`--raise-on-upload-error`
: Stop and submit nothing if any file fails to upload. By default, failed files are left out of the delivery. See [error handling](../error-handling.md).

`--max-concurrent-uploads INTEGER`
: Maximum number of files uploaded in parallel. Default: `5`.

`--chunk-size-mb INTEGER`
: Size in MB of the chunks in which files are split for multipart uploads. Default: `16`.

`--chunk-concurrency INTEGER`
: Number of chunks of a file uploaded in parallel. Default: `6`.

Example:

```bash
copernicusmarine-delivery upload --product-id my-product --dataset-id my-dataset --anchor local --source my/local/folder/file.nc
```

## delete

Request the deletion of files from a dataset. It submits a delivery with one delete operation.

```text
copernicusmarine-delivery delete --product-id PRODUCT_ID --dataset-id DATASET_ID --source SUFFIX [--source SUFFIX ...] [OPTIONS]
```

`--source TEXT`
: S3 MDS suffix of the file to delete, i.e. without product ID and dataset ID. Can be repeated. Required.

`--product-id TEXT`
: ID of the product. Required.

`--dataset-id TEXT`
: ID of the dataset. Required.

`--dry-run`
: Validate the delete without submitting anything.

`--save-delivery-json`
: Write the delivery document to `<delivery_id>.json`.

Example:

```bash
copernicusmarine-delivery delete --product-id my-product --dataset-id my-dataset --source some/folders/file.nc
```

## delivery

Submit a delivery with several operations, defined in a YAML file. The operations are run sequentially, in order.

```text
copernicusmarine-delivery delivery --product-id PRODUCT_ID --dataset-id DATASET_ID --file FILE [OPTIONS]
```

`--file TEXT`
: Path to the YAML file that defines the operations. Required. See the [delivery command](usage.md#delivery-command) for the format.

`--product-id TEXT`
: ID of the product. Required.

`--dataset-id TEXT`
: ID of the dataset. Required.

`--dry-run`, `--save-delivery-json`, `--raise-on-upload-error`, `--max-concurrent-uploads`, `--chunk-size-mb`, `--chunk-concurrency`
: Same as in [`upload`](#upload).

Example:

```bash
copernicusmarine-delivery delivery --product-id my-product --dataset-id my-dataset --file delivery_file.yaml
```

## status

Print the summary of a delivery fetched from the ingestion system.

```text
copernicusmarine-delivery status (--delivery-id DELIVERY_ID | --delivery-json FILE) [OPTIONS]
```

`--delivery-id TEXT`
: ID of the delivery.

`--delivery-json FILE`
: Path to a delivery document saved with `--save-delivery-json`.

`--show-all`
: List all the operations and files, with the error of each file, if any. By default, only the summary is shown.

One of `--delivery-id` or `--delivery-json` is required.

Example:

```bash
copernicusmarine-delivery status --delivery-id some-delivery-id --show-all
```

## list-deliveries

List the deliveries of your Pushing Entity, most recent first.

```text
copernicusmarine-delivery list-deliveries [OPTIONS]
```

`--timeframe [s|m|h|d|w|mo|y|all]`
: Only list deliveries created within this period counting back from now: second, minute, hour, day, week, month, year, or all. Default: `mo`.

Example:

```bash
copernicusmarine-delivery list-deliveries --timeframe w
```
