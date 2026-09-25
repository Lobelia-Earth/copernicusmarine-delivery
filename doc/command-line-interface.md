# CLI

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
copernicusmarine-delivery delivery --file delivery_file.yaml --dataset-id dataset_id --product-id product_id --pushing-entity-id pushing_entity
```

You can validate without performing any actual operation with `--dry-run`:

```bash
copernicusmarine-delivery delivery --file delivery_file.yaml --dataset-id dataset_id --product-id product_id --pushing-entity-id pushing_entity --dry-run

To save the delivery document to a JSON file (for later use with `copernicusmarine-delivery status`), use `--save-delivery-json`:

```bash
copernicusmarine-delivery delivery --file delivery_file.yaml --dataset-id dataset_id --product-id product_id --pushing-entity-id pushing_entity --save-delivery-json
```

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
copernicusmarine-delivery upload --source some/file.nc --source some/other/file.nc --dataset-id dataset_id --product-id product_id --pushing-entity-id pushing_entity
```

You can validate without performing any actual operation with `--dry-run`:

```bash
copernicusmarine-delivery upload --source some/file.nc --dataset-id dataset_id --product-id product_id --pushing-entity-id pushing_entity --dry-run
```

To save the delivery document to a JSON file (for later use with `copernicusmarine-delivery status`), use `--save-delivery-json`:

```bash
copernicusmarine-delivery upload --source some/file.nc --dataset-id dataset_id --product-id product_id --pushing-entity-id pushing_entity --save-delivery-json
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
copernicusmarine-delivery delete --source some/file.nc --source some/other/file.nc --dataset-id dataset_id --product-id product_id --pushing-entity-id pushing_entity
```

You can also use `--dry-run` and `--save-delivery-json` as with the upload command.

```{warning}
The path for the files should be the path without productID and datasetID. See the concept of [folder structure and path](concepts.md#folder-structure-and-path).
```

## Delivery status command

Given the delivery ID, prints the delivery summary fetched from OPDV.

```bash
copernicusmarine-delivery status --help
```

You can provide the IDs directly:

```bash
copernicusmarine-delivery status --delivery-id some-delivery-id --pushing-entity-id pushing_entity
```

Or provide a delivery JSON file (saved with `--save-delivery-json`):

```bash
copernicusmarine-delivery status --delivery-json some-delivery-id.json
```

## List deliveries command

List all the deliveries fetched from OPDV for a given pushing entity, printed as a list. If you want to see the details of a delivery, use the `status` command with the delivery ID or use the python interface.

```bash
copernicusmarine-delivery list-deliveries --help
```

```bash
copernicusmarine-delivery list-deliveries --pushing-entity-id pushing_entity
```
