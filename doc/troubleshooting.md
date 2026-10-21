# Troubleshooting

If the problem is not listed here, or persists after following the steps, please contact the MDS Service Desk. For general questions, see the [FAQ](faq.md).

```{note}
The messages below are the ones printed by the CLI. With the Python interface, the same errors are raised as exceptions with the same text, without the prefix (for example, `AuthenticationError`).
```

## Authentication errors

- **Missing credentials**

  ```text
  Value error: COPERNICUSMARINE_SERVICE_USERNAME environment variable is not set.
  ```

  The environment variable is not set in the shell where you run the tool. The same applies to `COPERNICUSMARINE_SERVICE_PASSWORD`. See [passing the credentials](credentials.md#passing-the-credentials).

- **Invalid credentials**

  ```text
  Authentication error: Could not get a token from https://auth.marine.copernicus.eu/realms/MIS/protocol/openid-connect/token (HTTP 400): Invalid user credentials. Please check your COPERNICUSMARINE_SERVICE_USERNAME and COPERNICUSMARINE_SERVICE_PASSWORD.
  ```

  The username or password is wrong. Check that the values are the ones of your Pushing Entity account, and that they have no extra spaces or quotes. If the credentials are right, the text after the HTTP code explains the reason. If you cannot solve it, contact the MDS Service Desk.

## Validation errors

These errors are raised before anything is uploaded.

- **Invalid Product ID or Dataset ID**

  ```text
  Invalid delivery ids error: my-product is not a valid Product ID for MY-PUSHING-ENTITY. Please ask User Support to register your Product if it is new.
  Invalid delivery ids error: my-dataset is not a valid Dataset ID for any Product for MY-PUSHING-ENTITY. Please ask User Support to register your Dataset if it is new.
  ```

  The ID has a typo, or it is not registered for your Pushing Entity. Check it. If it is new, contact the MDS Service Desk to register it.

- **Invalid files**

  ```text
  Invalid file: my/local/file.nc: File path does not exist.
  Invalid files error: Found 1 invalid files. See logs for details.
  ```

  One `Invalid file` line is printed for each file with a problem, followed by the summary. Nothing is uploaded. The reason can be:

  | Reason | What to do |
  | --- | --- |
  | `File path does not exist.` | Check the path and the directory you are running from. |
  | `File is empty.` | Remove the file from the delivery or regenerate it. |
  | `Duplicate file path.` | The same file is listed twice. Keep only one. |
  | `Expected anchor (...) was not found in local path` | The `--anchor` must be a folder name in the path of **all** the files. See [using the anchor](concepts.md#using-the-anchor). |
  | `No anchor specified and product_id (...) or dataset_id (...) found in local path` | Use an `--anchor`, or a relative path that does not contain the product or dataset ID. |
  | `Absolute paths are only allowed if an anchor is given` | Add an `--anchor` or use a relative path. |
  | `Key suffix derived from local path is not acceptable` | The path contains `../`, `//` or `:/`. Use an `--anchor` or a cleaner relative path. |

  See [folder structure and path](concepts.md#folder-structure-and-path) for how the paths are turned into the S3 MDS suffix.

- **All uploads failed**

  ```text
  No successful uploads error: All uploads failed. Errored files: [...]
  ```

  Every file of the operation failed to upload, so there is nothing to deliver. The reason of each file is printed in the logs just above.

- **Delivery rejected when submitted**

  The delivery exceeds the limits of the ingestion system (`Manifest validation failed: ...`). See [what happens if a limit is exceeded](best-practices.md#what-happens-if-a-limit-is-exceeded).
