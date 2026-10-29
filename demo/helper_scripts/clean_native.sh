#!/usr/bin/env bash
# DESTRUCTIVE: deletes ALL objects under native/ in the DTA bucket. Lists first, asks to confirm.
set -euo pipefail
BUCKET=mdl-native-20-dta
S5="s5cmd --profile mds-dta-read-write --endpoint-url https://s3.waw3-1.cloudferro.com/"

$S5 ls "s3://$BUCKET/native/*" || { echo "nothing under native/"; exit 0; }
read -rp "Delete ALL of the above from s3://$BUCKET/native/ ? type 'yes': " ans
[ "$ans" = yes ] || { echo aborted; exit 1; }
$S5 rm "s3://$BUCKET/native/*"
