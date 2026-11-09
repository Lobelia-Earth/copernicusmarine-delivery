# CLI reference

```{note}
`cm-de` is an alias of `copernicusmarine-delivery`.
```

## Synopsis

```text
copernicusmarine-delivery COMMAND [OPTIONS]
```

Use `copernicusmarine-delivery COMMAND --help` to print the help of a command.

## Environment variables

`COPERNICUSMARINE_SERVICE_USERNAME`
: Username of your Pushing Entity account. Required. See [credentials](../credentials.md).

`COPERNICUSMARINE_SERVICE_PASSWORD`
: Password of your Pushing Entity account. Required.

`PYTHON_LOG_DEBUG`
: Set it to `1`, `true` or `yes` to print debug logs.

## Exit statuses

`0`
: Success.

`1`
: The command failed. The error is logged. This also happens when the validation fails, when some files fail to upload, or when the `status` command reports a delivery as `failed` or `partially-failed`. The error is always printed to the standard error. With `--output json`, it is also printed to the standard output as a JSON object with the error in the `fatal_error` field. When some files fail to upload, or when `status` reports a failed delivery, the normal output is printed.

## Commands

```{eval-rst}
.. click:: copernicusmarine_delivery.command_line_interface:cli
   :prog: copernicusmarine-delivery
   :nested: full
```
