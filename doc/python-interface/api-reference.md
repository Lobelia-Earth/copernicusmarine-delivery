# API reference

All the objects below are importable from `copernicusmarine_delivery`.

## Operations

```{eval-rst}
.. autoclass:: copernicusmarine_delivery.Upload
   :members: add, submit

.. autoclass:: copernicusmarine_delivery.Delete
   :members: add, submit

.. autoclass:: copernicusmarine_delivery.Delivery
   :members: add, submit
```

## Delivery status

```{eval-rst}
.. autofunction:: copernicusmarine_delivery.delivery_status

.. autofunction:: copernicusmarine_delivery.list_deliveries
```

## Models

```{eval-rst}
.. autoclass:: copernicusmarine_delivery.core_functions.domain.ResponseUpload
   :members: delivery_id, fatal_error, files_uploaded, files_failed

.. autoclass:: copernicusmarine_delivery.core_functions.domain.ResponseDelete
   :members: delivery_id, fatal_error, files_to_delete

.. autoclass:: copernicusmarine_delivery.core_functions.domain.ResponseDelivery
   :members: delivery_id, fatal_error, operations_responses
```

## Exceptions

```{eval-rst}
.. autoexception:: copernicusmarine_delivery.InvalidDeliveryIdsError

.. autoexception:: copernicusmarine_delivery.InvalidFilesError

.. autoexception:: copernicusmarine_delivery.NoSuccessfulUploadsError
```
