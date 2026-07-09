from delivery_common.domain import PushingEntities


def get_ingestion_bucket_name(
    pushing_entity_id: str, pushing_entities: PushingEntities
) -> str | None:
    return next(
        (
            pu.bucket
            for pu in pushing_entities.pushing_entities
            if pu.name == pushing_entity_id
        ),
        None,
    )
