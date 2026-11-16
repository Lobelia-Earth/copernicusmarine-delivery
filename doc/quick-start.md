# Quick Start

Quick guide to set up and test the Copernicus Marine Delivery tool, using mostly the command line interface (CLI).

See the other pages for more detailed documentation.

## Get An Account

You need a **Copernicus Marine account** configured as your **Pushing Entity**.

Please, contact the MDS Service Desk to arrange it.

Once ready, load the account's credentials into environment variables:

```bash
export COPERNICUSMARINE_SERVICE_USERNAME="my-pe-account"
export COPERNICUSMARINE_SERVICE_PASSWORD="*************"
```

For more details, see [the page about credentials](credentials.md).

## Install

Install via pip and check that the installation was successful:

```bash
pip install copernicusmarine-delivery
copernicusmarine-delivery --help
```

For installation alternatives, see [the installation guide](installation.md).

## Staging environment

To prevent impacting the official MDS catalogue with the tests of the Copernicus Marine Delivery tool, a dedicated **staging environment** has been setup. Use the `--staging` flag to deliver the data to this staging environment:

#```bash
copernicusmarine-delivery --staging <OTHER-OPTIONS>
#```

#```{note}
All commands below use the `--staging` flag (`staging=True` in Python) to run against this staging environment. Remove it to run against production.
#```

Similarly, the `copernicusmarine` toolbox also has the `--staging` flag. Hence, the data you upload tot he MDS staging environment can be listed with `copernicusmarine get --staging --dry-run <OTHER-OPTIONS>`

## Test Access

You might want to check first that you can access the ingestion service and that you have the right credentials.

Run this command (that lists previous deliveries) to check that the account and the connection work:

```bash
copernicusmarine-delivery list-deliveries --staging
```

If there is an error, please contact the MDS Service Desk.

If the output is `No deliveries found.` or a list of deliveries, it means that the account is recognised as a Pushing Entity.

## Simple Upload

Create or select a file you have locally and upload it:

```bash
echo "hello" > test.nc
copernicusmarine-delivery upload --product-id <MY_PRODUCT> --dataset-id <MY_DATASET_WITH_TAG> --source test.nc --staging
```

Use a real Copernicus Marine product and dataset that belong to your Pushing Entity.

> [!NOTE]
> Refer to the paragraph about file paths in the [concepts page](concepts.md#folder-structure-and-path) to make sure you can map your local folder structure to the S3 MDS structure for your datasets.

> [!WARNING]  
> At this moment, delivered data is not published in the operational MDS, to facilitate testing. Hence, the data you upload will not be visible through the `copernicusmarine` toolbox.

> [!WARNING]  
> By using the `--staging` flag, delivered data is **not** published in the operational MDS.

## Check the delivery status

Check the status of the previous delivery:

```bash
copernicusmarine-delivery status --delivery-id <DELIVERY-ID> --staging
```

Where `DELIVERY-ID` is the one from the output of the upload/delete/delivery command. You can also list all deliveries to find the relevant delivery ID:

```bash
copernicusmarine-delivery list-deliveries --staging
```

## More complex delivery

Create a delivery YAML file (`delivery-test.yml`) with the following structure:

```yaml
# delivery-test.yml
delivery:
  - operation: delete
    files:
      - test.nc
  - operation: upload
    files:
      - my/local/files/file_01.nc
      - my/local/files/file_02.nc
```

This delivery will delete the file uploaded in the previous step and add 2 new files, preserving their subfolder structure.

The file has one entry per operation, run in the order written: `delete` takes the S3 MDS path of files already in MDS, `upload` takes local paths. See [the delivery file format](concepts.md#delivery-file-yaml) for all fields.

Make sure the new files exist. Otherwise, create them as follows:

```bash
mkdir -p my/local/files/
echo "hello 1" > my/local/files/file_01.nc
echo "hello 2" > my/local/files/file_02.nc
```

### Submit the delivery

```bash
copernicusmarine-delivery delivery --product-id <MY_PRODUCT> --dataset-id <MY_DATASET_WITH_TAG> --file delivery-test.yml --staging
```

Finally, check the status of this delivery:

```bash
copernicusmarine-delivery status --delivery-id <DELIVERY-ID> --staging
```

### Using an anchor

If your local folders do not match the MDS structure, add an `anchor` to the upload: the folder name after which the structure is kept. For instance, with local files in `/data/exports/my_dataset/2024/file_01.nc`:

```yaml
  - operation: upload
    anchor: my_dataset
    files:
      - /data/exports/my_dataset/2024/file_01.nc
```

The file is published as `<MY_PRODUCT>/<MY_DATASET_WITH_TAG>/2024/file_01.nc`: everything up to and including `my_dataset` is dropped. See [using the anchor](concepts.md#using-the-anchor) for the rules.


### Python snippet

The same delivery done in Python would look like this:

```python
from copernicusmarine_delivery import Delivery, Upload, Delete, delivery_status

delivery = Delivery(
    operations=[
        Delete(files=["test.nc"]),
        Upload(files=["my/local/files/file_01.nc", "my/local/files/file_02.nc"]),
    ]
)

response = delivery.submit(product_id="<MY_PRODUCT>", dataset_id="<MY_DATASET_WITH_TAG>", staging=True)

if not response.fatal_error:
    print(f"Delivery successful with delivery ID: {response.delivery_id}")
else:
    print(f"Delivery failed: {response.fatal_error}")

status = delivery_status(response.delivery_id, staging=True)

print(f"Delivery status: {status.model_dump_json(indent=2)}")
```

## Further reading

Now that the initial setup and test are done, please follow the rest of the documentation to understand how the Copernicus Marine Delivery tool can be used for your use case.
