# Draft deliveries

This page shows how to create, extend and publish a [draft delivery](concepts.md#draft-delivery), with the command line and with Python.

```{important}
Keep track of the delivery ID returned when the draft is created. It is the only thing that identifies the draft, and you need it to extend or publish it. If you lose it, you can find it again by listing your deliveries ([command line](command-line-interface/usage.md#list-deliveries-command) or [Python](python-interface/usage.md#list-deliveries)): drafts have the status `draft`. Use a wider timeframe if the draft is old.
```

The workflow is:

1. [Create](#draft-create) an empty draft. This gives you its delivery ID.
2. [Extend](#draft-extend) the draft with operations. This can be repeated.
3. [Publish](#draft-publish) the draft as it is saved.

(draft-create)=
## Create a draft

Creating a draft needs the dataset and the product. The draft is created empty: nothing is uploaded, and the operations are only added by extending it. It returns the delivery ID of the draft.

**Command line**

```bash
id=$(copernicusmarine-delivery draft create --dataset-id dataset_id --product-id product_id)
```

**Python**

```python
from copernicusmarine_delivery import draft

delivery_id = draft.create("product_id", "dataset_id")
```

(draft-extend)=
## Extend a draft

Extending a draft uploads the files of the operations and appends the operations to the draft, after the existing ones. It only needs the delivery ID of the draft: the product and the dataset are taken from the draft, so it can run from another session or from another machine. Operations are executed in the order they were added.

- At least one operation is required.
- It fails if the draft is not found, for example if it is already published.

**Command line**

With a YAML file, to add several operations at once (same structure as for the [delivery command](command-line-interface/usage.md#delivery-command)):

```bash
copernicusmarine-delivery draft extend --delivery-id "$id" --file delivery_file.yaml
```

Or with a single operation, without writing a file:

```bash
copernicusmarine-delivery draft extend --delivery-id "$id" --operation upload --source some/file.nc
```

See [the CLI usage](command-line-interface/usage.md#delivery-in-steps-drafts) for all the options.

**Python**

```python
from copernicusmarine_delivery import Delete, Upload, draft

draft.extend(delivery_id, [Upload(files=["some/file.nc"])])
draft.extend(
    delivery_id,
    [Delete(files=["some/old/file.nc"]), Upload(files=["some/other/file.nc"])],
)
```

(draft-publish)=
## Publish a draft

Publishing sends the draft as it is saved. It only needs the delivery ID. It fails if the draft is not found, for example if it is already published.

Once published, the delivery is processed like any other: check it with the delivery status ([command line](command-line-interface/usage.md#delivery-status-command) or [Python](python-interface/usage.md#wait-for-a-delivery)).

**Command line**

```bash
copernicusmarine-delivery draft publish --delivery-id "$id"
```

**Python**

```python
delivery = draft.publish(delivery_id)
```

## Dry run

Creating, extending and publishing a draft all accept a dry run (`--dry-run` on the command line, `dry_run=True` in Python). The draft is validated but nothing is saved, uploaded or published, so the draft can still be extended afterwards.
