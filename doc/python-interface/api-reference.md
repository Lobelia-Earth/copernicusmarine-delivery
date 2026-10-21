# API reference

All the objects below are importable from `copernicusmarine_delivery`.

## Operations

```{eval-rst}
.. autopydantic_model:: copernicusmarine_delivery.Upload
   :inherited-members: BaseModel

   .. automethod:: add
   .. automethod:: submit

.. autopydantic_model:: copernicusmarine_delivery.Delete
   :inherited-members: BaseModel

   .. automethod:: add
   .. automethod:: submit

.. autopydantic_model:: copernicusmarine_delivery.Delivery
   :inherited-members: BaseModel

   .. automethod:: add
   .. automethod:: submit
```

## Delivery status

```{eval-rst}
.. autofunction:: copernicusmarine_delivery.delivery_status

.. autofunction:: copernicusmarine_delivery.list_deliveries
```

## Models

```{eval-rst}
.. autopydantic_model:: copernicusmarine_delivery.ResponseUpload
   :inherited-members: BaseModel

.. autopydantic_model:: copernicusmarine_delivery.ResponseDelete
   :inherited-members: BaseModel

.. autopydantic_model:: copernicusmarine_delivery.ResponseDelivery
   :inherited-members: BaseModel
```

## Exceptions

```{eval-rst}
.. autoexception:: copernicusmarine_delivery.AuthenticationError

.. autoexception:: copernicusmarine_delivery.InvalidDeliveryIdsError

.. autoexception:: copernicusmarine_delivery.InvalidFilesError

.. autoexception:: copernicusmarine_delivery.NoSuccessfulUploadsError
```
