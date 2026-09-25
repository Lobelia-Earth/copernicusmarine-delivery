# Python Interface

The Python interface is designed so that you can build your delivery step by step and then submit it.

Here are some examples for simple upload and delete:

```python
from copernicusmarine_delivery import Upload, Delete

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
delete.submit(product_id, dataset_id)
upload.submit(product_id, dataset_id)
```

And here are some examples for complex deliveries:

```python
from copernicusmarine_delivery import Upload, Delete, Delivery

product_id = "some-product-id"
dataset_id = "some-dataset-id"

# Operations are executed in order
delivery = Delivery([
    Delete(["some/file.nc"]),
    Upload(["some/file.nc"]),
])
delivery.add(Delete(["some/other/file.nc"]))
delivery.add(Upload(["some/other/file.nc"]))

# --- submit ---
delivery.submit(product_id, dataset_id)
```

You can then check the status of your delivery with the delivery ID:

```python
from copernicusmarine_delivery import delivery_status

delivery = delivery_status(delivery_id)
```

You can also list all your deliveries:

```python
from copernicusmarine_delivery import list_deliveries

deliveries = list_deliveries()
```

It lists all your deliveries, sorted by delivery ID in descending order (most recent first). For example, if you want to have all the deliveries IDs for a given dataset, simply do:

```python
from copernicusmarine_delivery import list_deliveries

deliveries = list_deliveries()
dataset_deliveries = [
  d.delivery_id
  for d in deliveries
  if d.dataset_id == dataset_id
  ]
```
