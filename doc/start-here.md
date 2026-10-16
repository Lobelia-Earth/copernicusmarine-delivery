# Start here

Quick guide to setup and test the Copernicus Marine Delivery tool, using the command line interface (CLI).

See the other pages for more detailed documentation.

## Get an account

You need a **Copernicus Marine account** configured as your **Pushing Entity**.

Please, contact the MDS Service Desk to arrange it: `mds-service` at `lobelia.earth`.

Once ready, load the account's credentials in environment variables:

```bash
export COPERNICUSMARINE_SERVICE_USERNAME="my-pe-account"
export COPERNICUSMARINE_SERVICE_PASSWORD="*************"
```

For more details, see: [credentials.md](credentials.md)

## Install package

Install via pip and check that the installation was successful:

```bash
pip install copernicusmarine-delivery
copernicusmarine-delivery --help
```

For installation alternatives, see: [installation.md](installation.md)

## Test access

Run this command (that lists previous deliveries) to check that the account and the connection work:

```bash
copernicusmarine-delivery list-deliveries
```

If there is an error, please contact MDS Service Desk.

If the output is `No deliveries found.` or there is a list of deliveries, it means that the account is recognised as a Pushing Entity.

## Test a simple upload

Create a simple file and upload it:

```bash
echo "hello" > test.txt
copernicusmarine-delivery upload --product-id <MY_PRODUCT> --dataset-id <MY_DATATSET_WITH_TAG> --source test.txt 
```

Use a real Copernicus Marine product and dataset that belong to your Pushing Entity.

_Note: At this moment, delivered data is not published in the operaitonal MDS, to facilitate testing._

## Check the delivery status

Check the status of the previous delivery:

```bash
copernicusmarine-delivery status --delivery-id <DELIVERY-ID>
```

Where `DELIVERY-ID` was in the output of the previous command.

## Test a more complex upload

Create a delivery YAML file (`delivery-test.yml`) with the following structure:

```yaml
# delivery-test.yml
delivery:
  - operation: delete
    files:
      - test.txt
  - operation: upload
    files:
      - 2026/11/file_01.txt
      - 2026/11/file_02.txt
```

This delivery will delete the file uploaded in the previous step, and add 2 new files with its subfolder structure.

Make sure the new files exist:

```bash
mkdir -p 2026/11/
echo "hello 1" > 2026/11/file_01.txt
echo "hello 2" > 2026/11/file_02.txt
```

Submit the delivery:

```bash
copernicusmarine-delivery delivery --product-id <MY_PRODUCT> --dataset-id <MY_DATATSET_WITH_TAG> --file delivery-test.yml 
```

Finally, check the status of this delivery:

```bash
copernicusmarine-delivery status --delivery-id <DELIVERY-ID>
```

## Further reading

Now that the inital setup and test is done, please follow the rest of the documentation to understand how the Copernicus Marine Delivery tool can be used for your use case.
