# api/config/oidc_settings.py
"""
Identity-provider sign-in settings.

The UI starts the Authorization Code flow in the browser, but the
authorization code is exchanged for a token by the API, not by the browser.
That is what allows a **confidential** client to be used: its secret stays on
the Endpoint and never reaches the page.

It matters because the client an Endpoint gets is confidential. A Federation
registration creates one per Endpoint and hands back both its id and its
secret, so an Endpoint can offer identity-provider sign-in with what its own
registration already gave it, without a client having to be created for it by
hand in the realm.

A public client (no secret) works through the same path: the exchange simply
carries no client authentication, exactly as the browser used to send it.
"""

from pydantic_settings import BaseSettings


class OIDCSettings(BaseSettings):
    """
    Attributes
    ----------
    enabled : bool
        Whether identity-provider sign-in is offered at all.
    issuer : str
        Realm URL, e.g. https://idp.nationaldataplatform.org/realms/NDP. The
        token endpoint is read from its discovery document.
    client_id : str
        The client this Endpoint signs in through.
    client_secret : str
        Its secret, when the client is confidential. Empty for a public
        client, in which case the exchange sends no client authentication.
    """

    enabled: bool = False
    issuer: str = ""
    client_id: str = ""
    client_secret: str = ""

    model_config = {
        "env_file": ".env",
        "extra": "allow",
        "env_prefix": "OIDC_",
    }

    @property
    def is_configured(self) -> bool:
        """Whether sign-in has the values the flow cannot work without."""
        return bool(self.enabled and self.issuer and self.client_id)


oidc_settings = OIDCSettings()
