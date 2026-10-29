# Demo – CLI (success path)

User: `mds_test_2` (configured as Mercator → no `--pushing-entity-id` needed).

## 0. Setup (before the demo)

```bash
# from repo root
pixi shell          # makes `cm-de` available
source .env         # mds_test_2 credentials, ALLOW_HTTP, ENVIRONMENT=dta
unset PYTHON_LOG_DEBUG   # demo runs with INFO logs, not DEBUG

# clean + seed the bucket (delete targets must exist)
demo/clean_native.sh
cd demo && ./seed_delete_targets.sh

# yaml file paths are relative to the CWD
cd delivery_multiple_operations
```

## 1. Delivery (delete + upload)

The yaml deletes 4 files and uploads 16. 4 of the uploads re-use a deleted name (delete before upload).

```bash
cm-de delivery \
  --product-id GLOBAL_ANALYSISFORECAST_PHY_001_024 \
  --dataset-id cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i_202406 \
  --file delivery_multiple_operations.yaml
```

Copy the `delivery_id` from the output (format `YYYYMMDDTHHMMSS-GLOBAL_ANALYSISFORECAST_PHY_001_024-NNNN`).

Optional: validate without touching S3.

```bash
cm-de delivery --dry-run \
  --product-id GLOBAL_ANALYSISFORECAST_PHY_001_024 \
  --dataset-id cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i_202406 \
  --file delivery_multiple_operations.yaml
```

## 2. Status

```bash
export DELIVERY_ID=<delivery_id from above>

cm-de status --delivery-id $DELIVERY_ID              # summary
cm-de status --delivery-id $DELIVERY_ID --show-all   # every operation / file
```

## 3. List deliveries

```bash
cm-de list-deliveries --timeframe d     # last day
cm-de list-deliveries --timeframe all
```
