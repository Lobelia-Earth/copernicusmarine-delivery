# Python interface usage

The Python interface is designed so that you can build your delivery step by step and then submit it.

Here are some examples for simple upload and delete:

```python
from copernicusmarine_delivery import Upload, Delete

product_id = "some-product-id"
dataset_id = "some-dataset-id"

# --- Delete ---
delete = Delete(files=["some/file.nc", "some/other/file.nc"])

# --- Upload ---
upload = Upload(files=["some/file.nc", "some/other/file.nc"])

# --- Add files to upload or delete ---
delete.add("another/file.nc")
upload.add("another/file.nc")

# --- submit ---
delete.submit(product_id, dataset_id)
upload.submit(product_id, dataset_id)
```

And here are some examples for complex deliveries:

```python
from copernicusmarine_delivery import Upload, Delete, Delivery

product_id = "some-product-id"
dataset_id = "some-dataset-id"

# Operations are executed in order
delivery = Delivery(operations=[
    Delete(files=["some/file.nc"]),
    Upload(files=["some/file.nc"]),
])
delivery.add(Delete(files=["some/other/file.nc"]))
delivery.add(Upload(files=["some/other/file.nc"]))

# --- submit ---
delivery.submit(product_id, dataset_id)
```

You can then check the status of your delivery with the delivery ID:

```python
from copernicusmarine_delivery import delivery_status

delivery = delivery_status(delivery_id)
```

## Dry run

Use `dry_run=True` to validate a delivery before submitting it. The product, the dataset and the files are checked, but nothing is uploaded and no delivery is submitted. Since no delivery is submitted, you cannot check its status afterwards.

```python
response = delivery.submit(product_id, dataset_id, dry_run=True)
```

`dry_run` is also available when submitting a single `Upload` or `Delete`.

## Explore the response

`submit` returns a response with one entry per operation, in the same order as the delivery:

```python
response = delivery.submit(product_id, dataset_id)

print(response.fatal_error)  # None if nothing stopped the delivery
for operation_response in response.operations_responses:
    print(type(operation_response).__name__)
```

- An upload response has `files_uploaded` and `files_failed`.
- A delete response has `files_to_delete`.

See the [API reference](api-reference.md) for all the fields.

## Wait for a delivery

A delivery is processed after it is submitted. To wait until it finishes, check its status regularly:

```python
import time

from copernicusmarine_delivery import delivery_status

while True:
    status = delivery_status(response.delivery_id)
    if status.status.value in ("completed", "failed"):
        break
    time.sleep(10)

print(status.status.value, status.error_message)
```

## Example notebook

To try all of this step by step, download the {download}`example notebook <../_notebooks/submit_delivery.ipynb>`. It asks for your credentials when you run it, so they are not saved in the notebook.

## List deliveries

List all your deliveries:

```python
from copernicusmarine_delivery import list_deliveries

deliveries = list_deliveries()
```

It lists all your deliveries, sorted by delivery ID in descending order (most recent first). For example, if you want all the delivery IDs for a given dataset, simply do:

```python
from copernicusmarine_delivery import list_deliveries

deliveries = list_deliveries()
dataset_deliveries = [
  d.delivery_id
  for d in deliveries
  if d.dataset_id == dataset_id
  ]
```

By default, only the deliveries created within the last month are returned. Use the `timeframe` argument to change this window, counting back from the current time:

```python
from copernicusmarine_delivery import list_deliveries

# Only the deliveries created within the last week.
deliveries = list_deliveries(timeframe="w")

# All the deliveries, regardless of their creation date.
deliveries = list_deliveries(timeframe="all")
```

The available values are `"s"` (second), `"m"` (minute), `"h"` (hour), `"d"` (day), `"w"` (week), `"mo"` (month, the default), `"y"` (year) and `"all"`.
