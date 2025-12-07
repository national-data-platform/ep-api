# api/config/ckan_settings.py

import requests
from ckanapi import RemoteCKAN
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ckan_local_enabled: bool = False
    ckan_url: str = "http://localhost:5000"
    ckan_api_key: str = "your-api-key"
    ckan_verify_ssl: bool = True
    ckan_global_url: str = "https://nationaldataplatform.org/catalog"
    pre_ckan_enabled: bool = False
    pre_ckan_url: str = "https://ndp-test.sdsc.edu/catalog2"
    pre_ckan_api_key: str = ""
    pre_ckan_verify_ssl: bool = True

    def _get_session(self, verify_ssl: bool) -> requests.Session:
        """Create a requests session with SSL verification setting."""
        session = requests.Session()
        session.verify = verify_ssl
        return session

    @property
    def ckan(self):
        session = self._get_session(self.ckan_verify_ssl)
        return RemoteCKAN(self.ckan_url, apikey=self.ckan_api_key, session=session)

    @property
    def ckan_no_api_key(self):
        session = self._get_session(self.ckan_verify_ssl)
        return RemoteCKAN(self.ckan_url, session=session)

    @property
    def ckan_global(self):
        return RemoteCKAN(self.ckan_global_url)

    def _normalize_url(self, url: str) -> str:
        """Ensure URL has a scheme."""
        if url and not (url.startswith("http://") or url.startswith("https://")):
            return f"http://{url}"
        return url

    @property
    def pre_ckan(self):
        url = self._normalize_url(self.pre_ckan_url)
        session = self._get_session(self.pre_ckan_verify_ssl)
        return RemoteCKAN(url, apikey=self.pre_ckan_api_key, session=session)

    @property
    def pre_ckan_no_api_key(self):
        url = self._normalize_url(self.pre_ckan_url)
        session = self._get_session(self.pre_ckan_verify_ssl)
        return RemoteCKAN(url, session=session)

    model_config = {
        "env_file": ".env",
        "extra": "allow",
    }


ckan_settings = Settings()
