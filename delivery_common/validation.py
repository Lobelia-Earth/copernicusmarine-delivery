from delivery_common.domain import InvalidDeliveryIdsError, PushingEntity


def validate_delivery_ids(
    pushing_entity_id: str,
    product_id: str,
    dataset_id: str,
    pushing_entity: PushingEntity,
) -> None:
    valid_product = next(
        (
            product
            for product in pushing_entity.products
            if product.product_id == product_id
        ),
        None,
    )
    if not valid_product:
        raise InvalidDeliveryIdsError(
            f"{product_id} is not a valid Product ID for {pushing_entity_id}. "
            "Please ask User Support to register your Product if it is new."
        )
    if dataset_id not in valid_product.datasets:
        raise InvalidDeliveryIdsError(
            f"{dataset_id} is not a valid Dataset ID for any Product for {pushing_entity_id}. "
            "Please ask User Support to register your Dataset if it is new."
        )
