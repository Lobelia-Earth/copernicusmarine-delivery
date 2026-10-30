#!/usr/bin/env bash
# Seed the files that delivery_multiple_operations.yaml deletes, so OPDV finds them.
# Run from the demo/ directory.
set -euo pipefail
BUCKET=mdl-native-20-dta
PRODUCT=GLOBAL_ANALYSISFORECAST_PHY_001_024
DATASET=cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i_202406
SRC=delivery_multiple_operations
S5="s5cmd --profile mds-dta-read-write --endpoint-url https://s3.waw3-1.cloudferro.com/"

for f in \
  2026/05/glo12_rg_6h-i_20260528-18h_3D-uovo_nwct_R20260603.nc \
  2026/05/glo12_rg_6h-i_20260529-00h_3D-uovo_nwct_R20260603.nc \
  2026/06/glo12_rg_6h-i_20260602-06h_3D-uovo_nwct_R20260603.nc \
  2026/06/glo12_rg_6h-i_20260602-12h_3D-uovo_nwct_R20260603.nc; do
  $S5 cp "$SRC/$f" "s3://$BUCKET/native/$PRODUCT/$DATASET/$f"
done
$S5 ls "s3://$BUCKET/native/$PRODUCT/$DATASET/*"
