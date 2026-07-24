# Demo commands / fake data

## Data

You can find the demo data here: https://drive.google.com/drive/folders/11fyNCr_IDJvs4ny75spnETK-KRlAlywX

## Upload

This uploads four files and saves the delivery as a json

```
cd delivery_upload/
pusher upload --pushing-entity-id GLO-MERCATOR-TOULOUSE-FR --product-id GLOBAL_ANALYSISFORECAST_PHY_001_024 --dataset-id cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i_202406 --source 2026/05/glo12_rg_6h-i_20260527-06h_3D-uovo_nwct_R20260603.nc --source 2026/05/glo12_rg_6h-i_20260527-12h_3D-uovo_nwct_R20260603.nc --source 2026/05/glo12_rg_6h-i_20260527-18h_3D-uovo_nwct_R20260603.nc --source 2026/05/glo12_rg_6h-i_20260528-00h_3D-uovo_nwct_R20260603.nc --save-delivery-json
```

Check status
```
pusher status --delivery-json ...
```

## Delete
This commands deletes the files just uploaded. Can be repeated to force an error.

```
cd delivery_upload/
pusher delete --pushing-entity-id GLO-MERCATOR-TOULOUSE-FR --product-id GLOBAL_ANALYSISFORECAST_PHY_001_024 --dataset-id cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i_202406 --source 2026/05/glo12_rg_6h-i_20260527-06h_3D-uovo_nwct_R20260603.nc --source 2026/05/glo12_rg_6h-i_20260527-12h_3D-uovo_nwct_R20260603.nc --source 2026/05/glo12_rg_6h-i_20260527-18h_3D-uovo_nwct_R20260603.nc --source 2026/05/glo12_rg_6h-i_20260528-00h_3D-uovo_nwct_R20260603.nc --save-delivery-json
```
Check status
```
pusher status --delivery-json ...
```
## Delivery
This delivery will partially fail because when the poller checks it, it'll see that the files mentioned in the delete do not exist (if we run this on a clean bucket).

cd delivery_multiple_operations/

pusher delivery --pushing-entity-id GLO-MERCATOR-TOULOUSE-FR --product-id GLOBAL_ANALYSISFORECAST_PHY_001_024 --dataset-id cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i_202406 --file delivery_multiple_operations.yaml --save-delivery-json


## Early return error commands
### Wrong ids
#### Wrong pushing entity id
pusher delivery --pushing-entity-id GLO-MERCATOR-TOULOUSE --product-id GLOBAL_ANALYSISFORECAST_PHY_001_024 --dataset-id cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i_202406 --file delivery_multiple_operations.yaml --save-delivery-json

#### Wrong product id
pusher delivery --pushing-entity-id GLO-MERCATOR-TOULOUSE-FR --product-id GLOBAL_ANALYSISFORECAST --dataset-id cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i_202406 --file delivery_multiple_operations.yaml --save-delivery-json

#### Wrong dataset id
pusher delivery --pushing-entity-id GLO-MERCATOR-TOULOUSE-FR --product-id GLOBAL_ANALYSISFORECAST_PHY_001_024 --dataset-id cmems_mod_glo_phy-cur_anfc --file delivery_multiple_operations.yaml --save-delivery-json

#### Duplicate files
cd delivery_upload

pusher upload --pushing-entity-id GLO-MERCATOR-TOULOUSE-FR --product-id GLOBAL_ANALYSISFORECAST_PHY_001_024 --dataset-id cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i_202406 --source 2026/05/glo12_rg_6h-i_20260527-06h_3D-uovo_nwct_R20260603.nc --source 2026/05/glo12_rg_6h-i_20260527-06h_3D-uovo_nwct_R20260603.nc

## OPER TOOLS

### List all contents from given bucket
AWS_ACCESS_KEY_ID=$OPDV_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY=$OPDV_SECRET_ACCESS_KEY s5cmd --endpoint-url "$OPDV_S3_ENDPOINT" ls "s3://mdl-ing-glo-mercator-toulouse-fr-dta/*"

### Delete all contents from given bucket
AWS_ACCESS_KEY_ID=$OPDV_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY=$OPDV_SECRET_ACCESS_KEY s5cmd --endpoint-url "$OPDV_S3_ENDPOINT" rm "s3://mdl-ing-glo-mercator-toulouse-fr-dta/*"