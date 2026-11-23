# Compatibility shims

Code that lets this release work with older versions of the services it talks to, so it can ship before they are upgraded. Each entry says what it covers, where it is, and when it can be removed. When removing one, delete its code and tests and its entry here.

| Shim | Covers | Code | Remove when |
| ---- | ------ | ---- | ----------- |
| Approval without a client assertion (#433) | Endpoints installed before the service client (`OIDC_SERVICE_CLIENT_SECRET`) existed. They approve access requests without `X-Client-Assertion`, which the AAI in production does not check yet. | `_grant_via_aai` in `api/services/access_request_services/access_request_service.py`; `test_without_a_secret_approval_goes_without_the_assertion` | The AAI checks the calling app (sci-ndp/ndp-keycloak-aai#12) in production; from then on an Endpoint without the secret is refused anyway and must re-run the installer. |
| `GROUP_NAMES` names the client | Endpoints installed before `OIDC_SERVICE_CLIENT_ID`: an entry `ndp_ep/ep-<config-id>` gives `OIDC_SERVICE_CLIENT_ID=ep-<config-id>`. | `client_id_from_group_names` in `api/config/swagger_settings.py`; `tests/test_client_from_group_names.py` | Every Endpoint has re-run the installer, which writes `OIDC_SERVICE_CLIENT_ID`. |
