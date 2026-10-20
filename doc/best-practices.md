# Best practices

## Delivery limits

The ingestion system enforces the following limits **per delivery**:

- **Maximum number of files to upload: 150.** It counts the files of all the upload operations of the delivery. Deletes are not counted.
- **Maximum size of the delivery: 50 GB.** It is the sum of the size of all the files to upload.
- **Maximum size of a single file: 50 GB.** Larger files cannot be processed.

```{note}
These are the current values. They might change, so if you need to deliver more, please contact the MDS Service Desk.
```

### What happens if a limit is exceeded

The delivery is rejected when it is submitted, with a message like:

```text
HTTP error: Manifest validation failed: The total number of files to upload (200) exceeds the limit: 150
HTTP error: Manifest validation failed: Delivery size 60.0 GB is bigger than the server limits: 50.0 GB
```

If a file is bigger than the maximum size, the upload operation is not processed and all its files fail with `Cannot process upload operation: some files exceed the disk allowance.` You can see it with the [status](command-line-interface/usage.md#delivery-status-command) command and `--show-all`.

### Recommendations

- **Split large deliveries** into several deliveries, each within the limits. Remember that a delivery is for a single dataset, and that separate deliveries are processed in parallel. If the order matters (for example, a delete followed by an upload of the same file), keep those operations together in the same delivery.
- **Keep some margin** below the limits.
- **Prefer a few large files over many tiny ones**, within the limits, if your data format allows it.
- **Large files take longer.** To protect the disk of the ingestion system, the larger the files of an operation, the fewer files are processed in parallel. Very large deliveries can take a long time to be completed.
