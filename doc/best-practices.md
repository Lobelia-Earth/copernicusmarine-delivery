# Best practices

## Delivery limits

The ingestion system enforces the following limits **per delivery**:

- **Maximum number of files to upload: 150.** It counts the files of all the upload operations of the delivery. Deletes are not counted.
- **Maximum size of the delivery: 50 GB.** It is the sum of the size of all the files to upload.
- **Maximum size of a single file: 50 GB.** Larger files cannot be processed.

```{note}
These are the current values. They might change, so if you need to deliver more, please contact the MDS Service Desk.
```

```{note}
Sizes are counted in 1024-based units: **1 GB = 1,073,741,824 bytes**. Some tools, such as the macOS Finder, use 1000-based units and show bigger numbers for the same file. For example, a file of 45 GB here is shown as 48.3 GB in the Finder.
```

### What happens if a limit is exceeded

The delivery is rejected when it is submitted, with a message like:

```text
HTTP error: Manifest validation failed: The total number of files to upload (200) exceeds the limit: 150
HTTP error: Manifest validation failed: Delivery size 60.0 GB is bigger than the server limits: 50.0 GB
```

If a file is bigger than the maximum size, the upload operation is not processed and all its files fail with `Cannot process upload operation: some files exceed the disk allowance.` You can see it with the [status](command-line-interface/usage.md#delivery-status-command) command and `--show-all`.

### Recommendations

Do not go over the following values. They leave some margin below the limits:

| | Limit | Recommended maximum |
| --- | --- | --- |
| Files to upload per delivery | 150 | **135** |
| Size of a delivery | 50 GB | **45 GB** (48,318,382,080 bytes) |
| Size of a single file | 50 GB | **45 GB** (48,318,382,080 bytes) |

Other recommendations:

- **Split large deliveries** into several deliveries, each within the recommended maximums. To know how many you need, calculate it twice and keep the larger number:

  ```text
  deliveries needed by number of files = total number of files / maximum number of files
  deliveries needed by size            = total size / maximum size of a delivery
  ```

  For example, for a given release with 400 files of 1 GB each (400 GB in total), the above formulas result:

  - By number of files: 400 / 135 = 2.96, so 3 deliveries.
  - By size: 400 / 45 = 8.89, so 9 deliveries.
  - You need **9 deliveries**, the larger number. Each one has at most 45 files (45 GB).

- **Keep operations that depend on each other in the same delivery.** The operations of a delivery run in order, but separate deliveries are processed in parallel. For example, a delete followed by an upload of the same file must be in the same delivery. Remember that a delivery is for a single dataset.
- **Join small files into bigger ones**, if your data format allows it. Files smaller than about 341 MB (45 GB / 135 files) reach the maximum number of files before the maximum size, so you can send less data per delivery. Bigger files reach the maximum size first.
- **Large files take longer.** To protect the disk of the ingestion system, the bigger the files of an upload operation, the fewer of them are processed at the same time. It depends on the median size of the files of the operation (not the biggest one):

  ```text
  files processed at the same time = maximum size of a single file / median file size
  ```

  Round it down, with a minimum of 1 and a maximum of 10. Some examples:

  | Median file size of the operation | Files processed at the same time |
  | --- | --- |
  | 5 GB or less | 10 |
  | 7 GB | 7 |
  | 10 GB | 5 |
  | 25 GB | 2 |
  | 45 GB | 1 |

  Deliveries made of very large files can therefore take a long time to complete.
