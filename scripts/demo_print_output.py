"""Demo script to preview how the CLI print functions render in the terminal.

Run with:
    python scripts/demo_print_output.py
"""

from pathlib import Path

from copernicusmarine_delivery.command_line_interface import (
    print_delivery,
    print_delivery_summary,
    print_list_deliveries,
)
from copernicusmarine_delivery.core_functions.domain import (
    ErrorFile,
    ResponseDelete,
    ResponseUpload,
    S3KeySuffix,
)
from delivery_common.domain import (
    DeleteFile,
    DeleteOperation,
    Delivery,
    DeliveryStatus,
    UploadFile,
    UploadOperation,
)


def banner(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def example_upload_response() -> ResponseUpload:
    return ResponseUpload(
        delivery_id="20260928T101500-my_product-1234",
        files_uploaded=[
            (Path("local/data/temperature.nc"), S3KeySuffix("2026/temperature.nc")),
            (Path("local/data/salinity.nc"), S3KeySuffix("2026/salinity.nc")),
        ],
        files_failed=[
            ErrorFile(
                local_path=Path("local/data/corrupt.nc"),
                reason="Checksum mismatch",
            )
        ],
    )


def example_delete_response() -> ResponseDelete:
    return ResponseDelete(
        delivery_id="20260928T101500-my_product-1234",
        files_to_delete=[
            DeleteFile(key_suffix="2025/old_temperature.nc"),
            DeleteFile(key_suffix="2025/old_salinity.nc"),
        ],
    )


def example_delivery() -> Delivery:
    return Delivery(
        delivery_id="20260928T101500-my_product-1234",
        pushing_entity_id="my_entity",
        product_id="my_product",
        dataset_id="my_dataset",
        status=DeliveryStatus.completed,
        operations=[
            UploadOperation(
                files=[
                    UploadFile(
                        key_suffix="2026/temperature.nc",
                        file_size_mb=42,
                        checksum="abc123",
                        upload_start_time="2026-09-28T10:15:00Z",
                        upload_end_time="2026-09-28T10:15:05Z",
                    ),
                    UploadFile(
                        key_suffix="2026/corrupt.nc",
                        file_size_mb=7,
                        checksum="def456",
                        upload_start_time="2026-09-28T10:15:06Z",
                        upload_end_time="2026-09-28T10:15:07Z",
                        error_message="Checksum mismatch",
                    ),
                ]
            ),
            DeleteOperation(files=[DeleteFile(key_suffix="2025/old_temperature.nc")]),
        ],
    )


def example_failed_delivery() -> Delivery:
    return Delivery(
        delivery_id="20260927T083000-other_product-5678",
        pushing_entity_id="my_entity",
        product_id="other_product",
        dataset_id="other_dataset",
        status=DeliveryStatus.failed,
        error_message="Ingestion service rejected the delivery.",
    )


def main() -> None:
    delivery = example_delivery()
    responses = [example_upload_response(), example_delete_response()]

    banner("print_delivery_summary (dry run)")
    print_delivery_summary(delivery, responses, dry_run=True)

    banner("print_delivery_summary (real run)")
    print_delivery_summary(delivery, responses, dry_run=False)

    banner("print_delivery (summary only)")
    print_delivery(delivery, show_all=False)

    banner("print_delivery (show all)")
    print_delivery(delivery, show_all=True)

    banner("print_list_deliveries")
    print_list_deliveries([delivery, example_failed_delivery()])

    banner("print_list_deliveries (empty)")
    print_list_deliveries([])


if __name__ == "__main__":
    main()
