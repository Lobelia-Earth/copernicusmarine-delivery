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

## Test Access

You might want to check first that you can access the ingestion service and that you have the right credentials.

Run this command (that lists previous deliveries) to check that the account and the connection work:

```bash
copernicusmarine-delivery list-deliveries
```

If there is an error, please contact the MDS Service Desk.

If the output is `No deliveries found.` or a list of deliveries, it means that the account is recognised as a Pushing Entity.

## Simple Upload

Create or select a file you have locally and upload it:

```bash
echo "hello" > test.nc
copernicusmarine-delivery upload --product-id <MY_PRODUCT> --dataset-id <MY_DATASET_WITH_TAG> --source test.nc
```

Use a real Copernicus Marine product and dataset that belong to your Pushing Entity.

> [!NOTE]
> Refer to the paragraph about file paths in the [concepts page](concepts.md#folder-structure-and-path) to make sure you can map your local folder structure to the S3 MDS structure for your datasets.

> [!WARNING]  
> At this moment, delivered data is not published in the operational MDS, to facilitate testing. Hence, the data you upload will not be visible through the `copernicusmarine` toolbox.

## Check the delivery status

Check the status of the previous delivery:

```bash
copernicusmarine-delivery status --delivery-id <DELIVERY-ID>
```

Where `DELIVERY-ID` is the one from the output of the upload/delete/delivery command. You can also list all deliveries to find the relevant delivery ID:

```bash
copernicusmarine-delivery list-deliveries
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

Make sure the new files exist. Otherwise, create them as follows:

```bash
mkdir -p my/local/files/
echo "hello 1" > my/local/files/file_01.nc
echo "hello 2" > my/local/files/file_02.nc
```

Submit the delivery:

```bash
copernicusmarine-delivery delivery --product-id <MY_PRODUCT> --dataset-id <MY_DATASET_WITH_TAG> --file delivery-test.yml
```

Finally, check the status of this delivery:

```bash
copernicusmarine-delivery status --delivery-id <DELIVERY-ID>
```

The snippet in Python would look like this:

```python
from copernicusmarine_delivery import Delivery, Upload, Delete, delivery_status

delivery = Delivery(
  operations=[
    Delete(files=["test.nc"]),
    Upload(files=["my/local/files/file_01.nc", "my/local/files/file_02.nc"])
  ]
)

response = delivery.submit(product_id="<MY_PRODUCT>", dataset_id="<MY_DATASET_WITH_TAG>")

if not response.fatal_error:
    print(f"Delivery successful with delivery ID: {response.delivery_id}")
else:
    print(f"Delivery failed: {response.fatal_error}")

status = delivery_status(response.delivery_id)

print(f"Delivery status: {status.model_dump_json(indent=2)}")
```

## Further reading

Now that the initial setup and test are done, please follow the rest of the documentation to understand how the Copernicus Marine Delivery tool can be used for your use case.
