# Credentials

## Account

You need a **Copernicus Marine account** configured as your **Pushing Entity** in order to deliver data to the MDS.

If you do not have one, please contact the MDS Service Desk.

## Passing the credentials

You should set the following environment variables before running the `copernicusmarine-delivery` tool:

- `COPERNICUSMARINE_SERVICE_USERNAME`: your account username.
- `COPERNICUSMARINE_SERVICE_PASSWORD`: your account password.

Example:

```bash
# Store credentials in a .env file:
vim .env
export COPERNICUSMARINE_SERVICE_USERNAME="my-pe-account"
export COPERNICUSMARINE_SERVICE_PASSWORD="*************"

# Then use it:
source .env
copernicusmarine-delivery --help
```
