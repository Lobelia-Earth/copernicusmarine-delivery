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
: The command failed. The error is logged.

## Commands

```{eval-rst}
.. click:: copernicusmarine_delivery.command_line_interface:cli
   :prog: copernicusmarine-delivery
   :nested: full
```
