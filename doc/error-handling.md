# Error handling

This package will raise in the following cases:

- **Wrong IDs**: if the product ID or dataset ID are wrong, the package will raise an error.
- **Wrong file paths**: if the file paths are wrong and any of the files cannot be found locally, the package will raise an error. Applies for the "upload" operation.
- **Duplicate files**: if the same file is added twice to the same operation, the package will raise an error.
- **All the uploads for an operation fail**: if all the uploads for an operation fail, the package will raise an error.

Optionally, you can set the `raise_on_upload_error` flag to `True` when submitting a delivery. In that case, if any of the uploads fail, the package will raise an error. No delivery will be submitted in that case.
By default, the package will not raise an error if an upload fails. Instead, it will remove the failed uploads from the delivery. The failed uploads will be logged and can be found in the response.

```{note}
The error handling right now might be inconsistent across the package. Please report any inconsistency.
```
