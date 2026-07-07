from delivery_common.domain import InvalidDeliveryIds, PushingEntities


def validate_delivery_ids(
    pushing_entity_id: str,
    product_id: str,
    dataset_id: str,
    pushing_entities: PushingEntities,
) -> InvalidDeliveryIds | None:
    valid_pushing_entity = next(
        (e for e in pushing_entities.pushing_entities if e.name == pushing_entity_id),
        None,
    )
    if not valid_pushing_entity:
        return InvalidDeliveryIds(
            reason=f"{pushing_entity_id} is not a valid registered Pushing Entity"
        )
    valid_product = next(
        (
            product
            for product in valid_pushing_entity.products
            if product.product_id == product_id
        ),
        None,
    )
    if not valid_product:
        return InvalidDeliveryIds(
            reason=f"{product_id} is not a valid Product ID for {pushing_entity_id}"
        )
    if dataset_id not in valid_product.datasets:
        return InvalidDeliveryIds(
            reason=f"{dataset_id} is not a valid Dataset ID for any Product for {pushing_entity_id}"
        )
