#!/usr/bin/env python3
"""
Quick setup script for local development with LocalStack.
Creates a bucket, uploads the pushing_entities config and sample files.

Usage:
    python tests/resources/setup.py
"""

import argparse

import boto3
import yaml

ENDPOINT_URL = "http://localhost:4566"
BOTO_KWARGS = {
    "aws_access_key_id": "test",
    "aws_secret_access_key": "test",
    "region_name": "us-east-1",
}

PUSHING_ENTITY_ID = "DEV-STUDIO-LOCAL"
BUCKET_NAME = f"mdl-ing-{PUSHING_ENTITY_ID.lower()}"
METADATA_BUCKET = "mdl-metadata-dta"

PUSHING_ENTITIES_YAML = yaml.dump(
    {
        "pushing-entities": [
            {
                "name": PUSHING_ENTITY_ID,
                "bucket": BUCKET_NAME,
                "products": [
                    {"name": "product1", "datasets": ["dataset1", "dataset2"]},
                ],
            },
        ]
    }
)


def setup():
    s3 = boto3.client("s3", endpoint_url=ENDPOINT_URL, **BOTO_KWARGS)

    # Create buckets
    for bucket in (BUCKET_NAME, METADATA_BUCKET):
        s3.create_bucket(Bucket=bucket)
        print(f"Created bucket: {bucket}")

    # Upload pushing_entities config to metadata bucket
    s3.put_object(
        Bucket=METADATA_BUCKET,
        Key="pushing_entities.yml",
        Body=PUSHING_ENTITIES_YAML.encode(),
    )
    print(f"Uploaded pushing_entities.yml to {METADATA_BUCKET}")
    print(f"Use: ")
    print(f" pushing_entity_id={PUSHING_ENTITY_ID}")
    print(f" product_id=product1")
    print(f" dataset_id=dataset1 or dataset2")


def list_bucket():
    s3 = boto3.client("s3", endpoint_url=ENDPOINT_URL, **BOTO_KWARGS)
    print(f"Contents of bucket: {BUCKET_NAME}")
    try:
        response = s3.list_objects_v2(Bucket=BUCKET_NAME)
        if "Contents" in response:
            for obj in response["Contents"]:
                print(f"  {obj['Key']}")
        else:
            print("  (empty)")
    except Exception as e:
        print(f"Error listing bucket {BUCKET_NAME}: {e}")


def clean():
    s3 = boto3.client("s3", endpoint_url=ENDPOINT_URL, **BOTO_KWARGS)
    for bucket in (BUCKET_NAME, METADATA_BUCKET):
        try:
            response = s3.list_objects_v2(Bucket=bucket)
            if "Contents" in response:
                for obj in response["Contents"]:
                    s3.delete_object(Bucket=bucket, Key=obj["Key"])
                    print(f"Deleted {obj['Key']} from {bucket}")
            else:
                print(f"No objects to delete in {bucket}")
        except Exception as e:
            print(f"Error cleaning bucket {bucket}: {e}")

        # Delete the bucket itself
        try:
            s3.delete_bucket(Bucket=bucket)
            print(f"Deleted bucket: {bucket}")
        except Exception as e:
            print(f"Error deleting bucket {bucket}: {e}")

        # Delete the bucket itself
        try:
            s3.delete_bucket(Bucket=bucket)
            print(f"Deleted bucket: {bucket}")
        except Exception as e:
            print(f"Error deleting bucket {bucket}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup ministack for development.")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List the contents of the ingestion bucket instead of setting up.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean up the ingestion and metadata buckets.",
    )
    args = parser.parse_args()
    if args.list:
        list_bucket()
        exit(0)
    elif args.clean:
        clean()
        exit(0)

    setup()
