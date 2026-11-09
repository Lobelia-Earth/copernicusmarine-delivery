# CLI usage

```{note}
If you prefer a shorter command name, `copernicusmarine-delivery` has a convenient alias: `cm-de`.

All the following commands work with both `copernicusmarine-delivery` and its alias `cm-de`.
```

## Delivery command

Submit a delivery with possibly multiple operations based on a YAML file.

See the help for the inputs:

```bash
copernicusmarine-delivery delivery --help
```

Example:

```bash
copernicusmarine-delivery delivery --file delivery_file.yaml --dataset-id dataset_id --product-id product_id
```

You can validate without performing any actual operation with `--dry-run`:

```bash
copernicusmarine-delivery delivery --file delivery_file.yaml --dataset-id dataset_id --product-id product_id --dry-run
```

To save the delivery document to a JSON file (for later use with `copernicusmarine-delivery status`), use `--save-delivery-json`:

```bash
copernicusmarine-delivery delivery --file delivery_file.yaml --dataset-id dataset_id --product-id product_id --save-delivery-json
```

To print only the delivery ID instead of the full summary, use `--show-less`. This is useful in scripts:

```bash
copernicusmarine-delivery delivery --file delivery_file.yaml --dataset-id dataset_id --product-id product_id --show-less
```

To print the output as JSON, use `--output json`. The JSON goes to the standard output and the logs to the standard error, so you can pipe it to tools like `jq`:

```bash
copernicusmarine-delivery delivery --file delivery_file.yaml --dataset-id dataset_id --product-id product_id --output json
```

With `--show-less`, only the delivery ID is printed, as `{"delivery_id": "..."}`.

The delivery file should be a YAML file with the following structure:

```yaml
delivery:
  - operation: delete
    files:
      - tests/resources/file1.txt
      - tests/resources/file2.txt
  - operation: upload
    files:
      - tests/resources/file1.txt
      - tests/resources/file2.txt
    anchor: resources
```

## Upload command

Submit a delivery for one upload operation.

See the help for the inputs:

```bash
copernicusmarine-delivery upload --help
```

You can pass multiple sources:

```bash
copernicusmarine-delivery upload --source some/file.nc --source some/other/file.nc --dataset-id dataset_id --product-id product_id
```

You can validate without performing any actual operation with `--dry-run`:

```bash
copernicusmarine-delivery upload --source some/file.nc --dataset-id dataset_id --product-id product_id --dry-run
```

To save the delivery document to a JSON file (for later use with `copernicusmarine-delivery status`), use `--save-delivery-json`:

```bash
copernicusmarine-delivery upload --source some/file.nc --dataset-id dataset_id --product-id product_id --save-delivery-json
```

To print only the delivery ID instead of the full summary, use `--show-less`:

```bash
copernicusmarine-delivery upload --source some/file.nc --dataset-id dataset_id --product-id product_id --show-less
```

To print the output as JSON, use `--output json`:

```bash
copernicusmarine-delivery upload --source some/file.nc --dataset-id dataset_id --product-id product_id --output json
```

```{warning}
The path for the files should be relative. It should point to a local file.
The folder structure will also be reproduced when published.
```

## Delete command

Submit a delivery for one delete operation.

See the help for the inputs:

```bash
copernicusmarine-delivery delete --help
```

You can pass multiple sources:

```bash
copernicusmarine-delivery delete --source some/file.nc --source some/other/file.nc --dataset-id dataset_id --product-id product_id
```

You can also use `--dry-run`, `--save-delivery-json`, `--show-less` and `--output json` as with the upload command.

```{warning}
The path for the files should be the path without productID and datasetID. See the concept of [folder structure and path](../concepts.md#folder-structure-and-path).
```

## Delivery status command

Given the delivery ID, prints the delivery summary fetched from OPDV.

```bash
copernicusmarine-delivery status --help
```

You can provide the ID directly:

```bash
copernicusmarine-delivery status --delivery-id some-delivery-id
```

Or provide a delivery JSON file (saved with `--save-delivery-json`):

```bash
copernicusmarine-delivery status --delivery-json some-delivery-id.json
```

To get a more detailed view of the delivery, use the `--show-all` option with the `status` command. It lists all the files and prints any errors associated with each file.

```bash
copernicusmarine-delivery status --delivery-id some-delivery-id --show-all
```

To print only the delivery status (for example `published` or `partially-failed`), use `--show-less`:

```bash
copernicusmarine-delivery status --delivery-id some-delivery-id --show-less
```

To print the delivery as JSON, use `--output json`. With `--show-less`, only the status is printed, as `{"status": "..."}`.

```bash
copernicusmarine-delivery status --delivery-id some-delivery-id --output json
```

## List deliveries command

List all the deliveries fetched from OPDV, printed as a list. If you want to see the details of a delivery, use the `status` command with the delivery ID or use the Python interface.

```bash
copernicusmarine-delivery list-deliveries --help
```

```bash
copernicusmarine-delivery list-deliveries
```

By default, only the deliveries created within the last month are returned. Use the `--timeframe` option to change this window. The deliveries are filtered by their creation date, counting back from the current time.

```bash
copernicusmarine-delivery list-deliveries --timeframe w
```

The available values are:

| Value  | Timeframe            |
| ------ | -------------------- |
| `s`    | last second          |
| `m`    | last minute          |
| `h`    | last hour            |
| `d`    | last day             |
| `w`    | last week            |
| `mo`   | last month (default) |
| `y`    | last year            |
| `all`  | all deliveries       |

## Use the CLI in scripts

The exit status and the options `--show-less` and `--output json` make the commands easy to use in bash scripts. See the [exit statuses](reference.md#exit-statuses).

Suppose you have one file for each of five datasets of the same product, organised like this:

```text
DATASET_ID_1/2026/07/file_name.nc
DATASET_ID_2/2026/07/file_name.nc
DATASET_ID_3/2026/07/file_name.nc
DATASET_ID_4/2026/07/file_name.nc
DATASET_ID_5/2026/07/file_name.nc
```

A delivery is for one dataset, so you want to create five deliveries, one per dataset, and then wait until all of them are finished.

### Submit the files

With `--show-less`, the upload command only prints the delivery ID. The logs go to the standard error, so they are still shown but they are not captured by `$(...)`. The dataset ID is also used as the `--anchor`, so the files are published as `2026/07/file_name.nc` in each dataset. See the [folder structure and path](../concepts.md#folder-structure-and-path):

```bash
dataset_ids=(DATASET_ID_1 DATASET_ID_2 DATASET_ID_3 DATASET_ID_4 DATASET_ID_5)

ids=()
for dataset_id in "${dataset_ids[@]}"; do
    id=$(copernicusmarine-delivery upload \
        --product-id PRODUCT_ID --dataset-id "$dataset_id" \
        --source "$dataset_id/2026/07/file_name.nc" --anchor "$dataset_id" \
        --show-less)
    [ $? -ne 0 ] && echo "Upload to $dataset_id finished with errors" >&2
    [ -n "$id" ] && ids+=("$id")
done
```

If some files fail to upload but others succeed, the command prints the delivery ID and exits with `1`. That is why the exit status is checked separately from the ID. If the command stops with an error, nothing is printed and `id` is empty.

### Wait for the deliveries

Once submitted, a delivery is processed. Check the status of each delivery until it is in a [final status](../concepts.md#delivery-status). With `--show-less`, the status command only prints the status, and it exits with `1` if the status is `failed` or `partially-failed`:

```bash
pending=("${ids[@]}")
exit_code=0
while [ ${#pending[@]} -gt 0 ]; do
    still_pending=()
    for id in "${pending[@]}"; do
        status=$(copernicusmarine-delivery status --delivery-id "$id" --show-less)
        case "$status" in
            published)
                echo "$id published" ;;
            failed|partially-failed)
                echo "$id $status"
                exit_code=1 ;;
            *)
                echo "Still waiting: $id $status"
                still_pending+=("$id") ;;
        esac
    done
    pending=("${still_pending[@]}")
    [ ${#pending[@]} -gt 0 ] && sleep 10
done
exit $exit_code
```

If the status command stops with an error, for example because of a network issue, nothing is printed and the delivery is checked again in the next round. In a real script, consider adding a maximum waiting time.

The output of the whole script could look like this:

```text
2026-11-09 11:46:05 - copernicusmarine-delivery - INFO - Starting to upload 1 files ...
2026-11-09 11:46:07 - copernicusmarine-delivery - INFO - Uploaded [1/1] file file_name.nc
2026-11-09 11:46:07 - copernicusmarine-delivery - INFO - Finished uploading 1 files for a total size of 10.00 MB.
2026-11-09 11:46:08 - copernicusmarine-delivery - INFO - Starting to upload 1 files ...
2026-11-09 11:46:09 - copernicusmarine-delivery - INFO - Uploaded [1/1] file file_name.nc
2026-11-09 11:46:09 - copernicusmarine-delivery - INFO - Finished uploading 1 files for a total size of 7.00 MB.
2026-11-09 11:46:11 - copernicusmarine-delivery - INFO - Starting to upload 1 files ...
2026-11-09 11:46:12 - copernicusmarine-delivery - INFO - Uploaded [1/1] file file_name.nc
2026-11-09 11:46:12 - copernicusmarine-delivery - INFO - Finished uploading 1 files for a total size of 5.00 MB.
2026-11-09 11:46:13 - copernicusmarine-delivery - INFO - Starting to upload 1 files ...
2026-11-09 11:46:14 - copernicusmarine-delivery - INFO - Uploaded [1/1] file file_name.nc
2026-11-09 11:46:14 - copernicusmarine-delivery - INFO - Finished uploading 1 files for a total size of 8.00 MB.
2026-11-09 11:46:15 - copernicusmarine-delivery - INFO - Starting to upload 1 files ...
2026-11-09 11:46:17 - copernicusmarine-delivery - INFO - Uploaded [1/1] file file_name.nc
2026-11-09 11:46:17 - copernicusmarine-delivery - INFO - Finished uploading 1 files for a total size of 6.00 MB.
20261109T114605-PRODUCT_ID-9295 published
Still waiting: 20261109T114608-PRODUCT_ID-4279 validated
Still waiting: 20261109T114611-PRODUCT_ID-4488 validated
Still waiting: 20261109T114613-PRODUCT_ID-1730 pending
Still waiting: 20261109T114615-PRODUCT_ID-6051 pending
20261109T114608-PRODUCT_ID-4279 published
20261109T114611-PRODUCT_ID-4488 published
Still waiting!: 20261109T114613-PRODUCT_ID-1730 validated
20261109T114615-PRODUCT_ID-6051 published
20261109T114613-PRODUCT_ID-1730 published
```

### Read the output as JSON

With `--output json`, the output is JSON that you can parse with a tool like [jq](https://jqlang.org/). Together with `--show-less`, the upload command prints `{"delivery_id": "..."}`:

```bash
out=$(copernicusmarine-delivery upload \
    --product-id PRODUCT_ID --dataset-id DATASET_ID_1 \
    --source DATASET_ID_1/2026/07/file_name.nc --anchor DATASET_ID_1 \
    --show-less --output json)
echo "$out" | jq -r '.delivery_id // empty'
```

If the command stops with an error, the JSON has the error in the `fatal_error` field instead:

```bash
echo "$out" | jq -r '.fatal_error // empty'
```
