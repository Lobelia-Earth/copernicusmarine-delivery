# FAQ

For help with a specific error message, see [troubleshooting](troubleshooting.md).

## Account

### How do I get an account and credentials?

You need a Copernicus Marine account configured as your Pushing Entity. See [credentials](credentials.md#account) to get one, and [passing the credentials](credentials.md#passing-the-credentials) to set it up.

## Deliveries

### How many files and how much data can I send in one delivery?

At most 150 files to upload and 50 GB per delivery, and no single file can be bigger than 50 GB. See [delivery limits](best-practices.md#delivery-limits).

### What can I do if my data is bigger than the limits?

Split it into several deliveries. See the [recommendations](best-practices.md#recommendations).

### Can one delivery contain several datasets?

No. A delivery is for a single dataset, so submit one delivery per dataset. See [delivery](concepts.md#delivery).

## Status

### How do I know if my delivery is going well?

Check its status with the delivery ID you got when submitting it. See the [status command](command-line-interface/usage.md#delivery-status-command) for the CLI or [delivery status](python-interface/api-reference.md#delivery-status) for the Python interface.

### I lost my delivery ID. How can I find it?

List your recent deliveries. See the [list deliveries command](command-line-interface/usage.md#list-deliveries-command).

### What happens if some of the files fail to upload?

By default, the failed files are removed from the delivery and logged, and the rest is delivered. See [error handling](error-handling.md).
