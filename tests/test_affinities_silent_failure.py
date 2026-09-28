"""A failed Affinities link is reported instead of swallowed (issue #281)."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient

from api.services.affinities_services.affinities_client import AffinitiesClient

EP_UUID = "550e8400-e29b-41d4-a716-446655440000"
RECORD_UID = "12345678-1234-1234-1234-123456789abc"
TRIPLE_UID = "abcdef00-0000-4000-8000-000000000001"

SETTINGS = "api.services.affinities_services.affinities_client.affinities_settings"
HTTPX = "api.services.affinities_services.affinities_client.httpx.AsyncClient"


@pytest.fixture(autouse=True)
def _no_cached_probe():
    """The probe cache is class level, so it would leak between tests."""
    AffinitiesClient._registration_cache = None
    yield
    AffinitiesClient._registration_cache = None


def _response(payload, status_code=200):
    """A response shaped the way the client reads it."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    response.text = str(payload)

    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=response
        )
    else:
        response.raise_for_status = MagicMock()

    return response


class FakeAffinities:
    """
    An Affinities that answers per path and records what it was asked.

    Nothing here mocks the client's own methods, so the decision to skip the
    triple has to show up as a request that was never made.
    """

    def __init__(self, link_status=200):
        self.link_status = link_status
        self.paths = []

    def request(self, method=None, url=None, json=None):
        self.paths.append(url)

        if url.endswith("/datasets") or url.endswith("/services"):
            return _response({"uid": RECORD_UID})
        if url.endswith("-endpoints"):
            return _response({}, self.link_status)
        if url.endswith("/affinities"):
            return _response({"triple_uid": TRIPLE_UID})

        raise AssertionError("unexpected request to " + str(url))

    def get(self, url):
        self.paths.append(url)
        return _response({"uid": EP_UUID})


def _configured_settings(mock_settings):
    mock_settings.is_configured = True
    mock_settings.url = "http://affinities:8000"
    mock_settings.ep_uuid = EP_UUID
    mock_settings.timeout = 30


def _fake_httpx(mock_client_class, fake):
    client = AsyncMock()
    client.request = AsyncMock(side_effect=fake.request)
    client.get = AsyncMock(side_effect=fake.get)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    mock_client_class.return_value = client
    return client


class TestAFailedLinkStopsTheTriple:
    """
    The bug: the link was attempted, its result ignored, and the triple
    created regardless -- so Affinities ended up holding a triple naming an
    endpoint it does not have, while the registration reported success.
    """

    @pytest.mark.asyncio
    @patch(HTTPX)
    async def test_no_triple_is_created_for_an_unlinked_dataset(self, mock_httpx):
        fake = FakeAffinities(link_status=404)

        with patch(SETTINGS) as mock_settings:
            _configured_settings(mock_settings)
            _fake_httpx(mock_httpx, fake)

            await AffinitiesClient().register_dataset(title="Test Dataset")

        assert not any(path.endswith("/affinities") for path in fake.paths)

    @pytest.mark.asyncio
    @patch(HTTPX)
    async def test_a_linked_dataset_still_gets_its_triple(self, mock_httpx):
        """The guard must not cost the successful path its triple."""
        fake = FakeAffinities(link_status=200)

        with patch(SETTINGS) as mock_settings:
            _configured_settings(mock_settings)
            _fake_httpx(mock_httpx, fake)

            await AffinitiesClient().register_dataset(title="Test Dataset")

        assert any(path.endswith("/affinities") for path in fake.paths)

    @pytest.mark.asyncio
    @patch(HTTPX)
    async def test_no_triple_is_created_for_an_unlinked_service(self, mock_httpx):
        fake = FakeAffinities(link_status=404)

        with patch(SETTINGS) as mock_settings:
            _configured_settings(mock_settings)
            _fake_httpx(mock_httpx, fake)

            await AffinitiesClient().register_service(service_type="api")

        assert not any(path.endswith("/affinities") for path in fake.paths)

    @pytest.mark.asyncio
    @patch(HTTPX)
    async def test_a_linked_service_still_gets_its_triple(self, mock_httpx):
        fake = FakeAffinities(link_status=200)

        with patch(SETTINGS) as mock_settings:
            _configured_settings(mock_settings)
            _fake_httpx(mock_httpx, fake)

            await AffinitiesClient().register_service(service_type="api")

        assert any(path.endswith("/affinities") for path in fake.paths)

    @pytest.mark.asyncio
    @patch(HTTPX)
    async def test_the_uuid_is_still_returned_so_the_record_is_reachable(
        self, mock_httpx
    ):
        """
        The record exists in Affinities whatever happened to the link, and
        this UUID is the only way back to it: the caller writes it to the
        dataset as ndp_affinity_uuid. Dropping it would orphan the record.
        """
        with patch(SETTINGS) as mock_settings:
            _configured_settings(mock_settings)
            _fake_httpx(mock_httpx, FakeAffinities(link_status=404))

            result = await AffinitiesClient().register_dataset(title="Test Dataset")

        assert result == UUID(RECORD_UID)

    @pytest.mark.asyncio
    @patch(HTTPX)
    async def test_a_failed_registration_is_not_a_failed_request(self, mock_httpx):
        """Registering must stay tolerant: a refused link is not a raise."""
        with patch(SETTINGS) as mock_settings:
            _configured_settings(mock_settings)
            _fake_httpx(mock_httpx, FakeAffinities(link_status=500))

            # No pytest.raises: the point is that nothing propagates.
            assert await AffinitiesClient().register_dataset(title="D") is not None


class TestTheFailureIsReported:
    """Before this, the only trace was a bare transport error from _request."""

    @pytest.mark.asyncio
    @patch(HTTPX)
    async def test_the_log_names_the_endpoint_and_the_setting(self, mock_httpx, caplog):
        with patch(SETTINGS) as mock_settings:
            _configured_settings(mock_settings)
            _fake_httpx(mock_httpx, FakeAffinities(link_status=404))

            with caplog.at_level(logging.ERROR):
                await AffinitiesClient().register_dataset(title="Test Dataset")

        logged = caplog.text
        assert EP_UUID in logged
        assert "AFFINITIES_EP_UUID" in logged
        assert RECORD_UID in logged

    @pytest.mark.asyncio
    @patch(HTTPX)
    async def test_the_skipped_triple_is_logged_as_an_error(self, mock_httpx, caplog):
        with patch(SETTINGS) as mock_settings:
            _configured_settings(mock_settings)
            _fake_httpx(mock_httpx, FakeAffinities(link_status=404))

            with caplog.at_level(logging.ERROR):
                await AffinitiesClient().register_dataset(title="Test Dataset")

        errors = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert any("triple" in r.getMessage() for r in errors)

    @pytest.mark.asyncio
    @patch(HTTPX)
    async def test_nothing_is_logged_as_an_error_when_the_link_works(
        self, mock_httpx, caplog
    ):
        with patch(SETTINGS) as mock_settings:
            _configured_settings(mock_settings)
            _fake_httpx(mock_httpx, FakeAffinities(link_status=200))

            with caplog.at_level(logging.ERROR):
                await AffinitiesClient().register_dataset(title="Test Dataset")

        assert [r for r in caplog.records if r.levelno == logging.ERROR] == []

    @pytest.mark.asyncio
    @patch(HTTPX)
    async def test_the_relationship_call_reports_false(self, mock_httpx):
        with patch(SETTINGS) as mock_settings:
            _configured_settings(mock_settings)
            _fake_httpx(mock_httpx, FakeAffinities(link_status=404))

            linked = await AffinitiesClient().create_dataset_endpoint_relationship(
                UUID(RECORD_UID)
            )

        assert linked is False


class TestCheckRegistration:
    """
    AFFINITIES_EP_UUID is issued by Affinities and was never verified, so a
    value from another instance, or a typo, failed on every write and
    nowhere else.
    """

    @staticmethod
    async def _probe(get_response):
        with patch(SETTINGS) as mock_settings:
            _configured_settings(mock_settings)
            with patch(HTTPX) as mock_httpx:
                client = AsyncMock()
                client.get = AsyncMock(return_value=get_response)
                client.__aenter__ = AsyncMock(return_value=client)
                client.__aexit__ = AsyncMock(return_value=None)
                mock_httpx.return_value = client

                return await AffinitiesClient().check_registration()

    @pytest.mark.asyncio
    async def test_a_known_endpoint_is_registered(self):
        probe = await self._probe(_response({"uid": EP_UUID}))

        assert probe["reachable"] is True
        assert probe["endpoint_registered"] is True
        assert probe["detail"] is None

    @pytest.mark.asyncio
    async def test_an_unknown_endpoint_is_reported_with_the_way_out(self):
        probe = await self._probe(_response({"detail": "Endpoint not found"}, 404))

        assert probe["reachable"] is True
        assert probe["endpoint_registered"] is False
        assert EP_UUID in probe["detail"]
        assert "AFFINITIES_EP_UUID" in probe["detail"]

    @pytest.mark.asyncio
    async def test_a_malformed_uuid_leaves_the_question_unanswered(self):
        """Affinities answers 422 for a value that is not a UUID at all."""
        probe = await self._probe(_response({"detail": "uuid_parsing"}, 422))

        assert probe["reachable"] is True
        assert probe["endpoint_registered"] is None
        assert "422" in probe["detail"]

    @pytest.mark.asyncio
    async def test_an_unreachable_affinities_is_not_an_unregistered_endpoint(self):
        """Not knowing is reported as not knowing, not as a missing endpoint."""
        with patch(SETTINGS) as mock_settings:
            _configured_settings(mock_settings)
            with patch(HTTPX) as mock_httpx:
                client = AsyncMock()
                client.get = AsyncMock(
                    side_effect=httpx.ConnectError("Connection refused")
                )
                client.__aenter__ = AsyncMock(return_value=client)
                client.__aexit__ = AsyncMock(return_value=None)
                mock_httpx.return_value = client

                probe = await AffinitiesClient().check_registration()

        assert probe["reachable"] is False
        assert probe["endpoint_registered"] is None
        assert "ConnectError" in probe["detail"]

    @pytest.mark.asyncio
    async def test_the_probe_does_not_wait_the_configured_timeout(self):
        """
        A readiness probe blocked for the 30s default would be worse than the
        problem it reports.
        """
        with patch(SETTINGS) as mock_settings:
            _configured_settings(mock_settings)
            with patch(HTTPX) as mock_httpx:
                client = AsyncMock()
                client.get = AsyncMock(return_value=_response({"uid": EP_UUID}))
                client.__aenter__ = AsyncMock(return_value=client)
                client.__aexit__ = AsyncMock(return_value=None)
                mock_httpx.return_value = client

                await AffinitiesClient().check_registration()

        used = mock_httpx.call_args.kwargs["timeout"]
        assert used <= AffinitiesClient.READINESS_TIMEOUT_SECONDS
        assert used < 30

    @pytest.mark.asyncio
    async def test_the_endpoint_uuid_is_the_one_asked_about(self):
        with patch(SETTINGS) as mock_settings:
            _configured_settings(mock_settings)
            with patch(HTTPX) as mock_httpx:
                client = AsyncMock()
                client.get = AsyncMock(return_value=_response({"uid": EP_UUID}))
                client.__aenter__ = AsyncMock(return_value=client)
                client.__aexit__ = AsyncMock(return_value=None)
                mock_httpx.return_value = client

                await AffinitiesClient().check_registration()

        assert client.get.call_args.args[0].endswith("/ep/" + EP_UUID)


class TestReadyReportsAffinities:
    """What an operator can now see without reading the logs."""

    CLIENT = "api.services.affinities_services.AffinitiesClient"

    @staticmethod
    def _client(enabled=True, probe=None):
        client = MagicMock()
        client.is_enabled = enabled
        client.check_registration = AsyncMock(return_value=probe)
        return client

    def _ready(self, client):
        from api.main import app

        with (
            patch(self.CLIENT, return_value=client),
            patch("api.routes.health_routes.ready._check_local_catalog") as catalog,
            patch("api.routes.health_routes.ready._check_pre_ckan") as pre_ckan,
            patch("api.routes.health_routes.ready._check_minio") as minio,
            patch("api.routes.health_routes.ready._check_kafka") as kafka,
        ):
            catalog.return_value = {"status": "disabled"}
            pre_ckan.return_value = {"status": "disabled"}
            minio.return_value = {"status": "disabled"}
            kafka.return_value = {"status": "disabled"}

            return TestClient(app).get("/ready")

    def test_a_disabled_integration_is_reported_as_disabled(self):
        response = self._ready(self._client(enabled=False))

        assert response.json()["checks"]["affinities"] == {"status": "disabled"}

    def test_a_registered_endpoint_reports_up(self):
        response = self._ready(
            self._client(
                probe={
                    "reachable": True,
                    "endpoint_registered": True,
                    "detail": None,
                }
            )
        )
        check = response.json()["checks"]["affinities"]

        assert check["status"] == "up"
        assert check["endpoint_registered"] is True
        assert "detail" not in check

    def test_an_unknown_endpoint_is_visible_without_failing_readiness(self):
        """
        Reported, not enforced: the same call this made before answered 200
        with everything healthy, and Affinities serves no request, so a
        deployment is not taken out of rotation over it.
        """
        response = self._ready(
            self._client(
                probe={
                    "reachable": True,
                    "endpoint_registered": False,
                    "detail": "Affinities does not know endpoint " + EP_UUID,
                }
            )
        )

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

        check = response.json()["checks"]["affinities"]
        assert check["status"] == "up"
        assert check["endpoint_registered"] is False
        assert EP_UUID in check["detail"]

    def test_an_unreachable_affinities_does_not_take_the_endpoint_down(self):
        response = self._ready(
            self._client(
                probe={
                    "reachable": False,
                    "endpoint_registered": None,
                    "detail": "ConnectError: Connection refused",
                }
            )
        )

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["checks"]["affinities"]["status"] == "down"

    def test_a_real_dependency_still_fails_readiness(self):
        """The exception is Affinities alone, not the verdict itself."""
        from api.main import app

        client = self._client(
            probe={"reachable": True, "endpoint_registered": True, "detail": None}
        )

        with (
            patch(self.CLIENT, return_value=client),
            patch("api.routes.health_routes.ready._check_local_catalog") as catalog,
            patch("api.routes.health_routes.ready._check_pre_ckan") as pre_ckan,
            patch("api.routes.health_routes.ready._check_minio") as minio,
            patch("api.routes.health_routes.ready._check_kafka") as kafka,
        ):
            catalog.return_value = {"status": "down", "error": "Connection refused"}
            pre_ckan.return_value = {"status": "disabled"}
            minio.return_value = {"status": "disabled"}
            kafka.return_value = {"status": "disabled"}

            response = TestClient(app).get("/ready")

        assert response.status_code == 503
        assert response.json()["status"] == "unhealthy"


class TestTheProbeIsCached:
    """
    /ready is called on a schedule. An unreachable Affinities costs whole
    seconds per call, and a readiness probe that times out takes the
    container out of rotation -- which is what keeping Affinities out of the
    verdict exists to prevent.
    """

    @staticmethod
    def _client_with(mock_httpx):
        client = AsyncMock()
        client.get = AsyncMock(return_value=_response({"uid": EP_UUID}))
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        mock_httpx.return_value = client
        return client

    @pytest.mark.asyncio
    async def test_a_second_probe_does_not_reach_affinities(self):
        with patch(SETTINGS) as mock_settings:
            _configured_settings(mock_settings)
            with patch(HTTPX) as mock_httpx:
                http = self._client_with(mock_httpx)

                first = await AffinitiesClient().check_registration()
                second = await AffinitiesClient().check_registration()

        assert http.get.await_count == 1
        assert second == first

    @pytest.mark.asyncio
    async def test_a_changed_endpoint_uuid_is_probed_again(self):
        """A cache that survived a configuration change would hide it."""
        with patch(SETTINGS) as mock_settings:
            _configured_settings(mock_settings)
            with patch(HTTPX) as mock_httpx:
                http = self._client_with(mock_httpx)

                await AffinitiesClient().check_registration()
                mock_settings.ep_uuid = "00000000-0000-4000-8000-000000000000"
                await AffinitiesClient().check_registration()

        assert http.get.await_count == 2

    @pytest.mark.asyncio
    async def test_an_expired_result_is_probed_again(self):
        with patch(SETTINGS) as mock_settings:
            _configured_settings(mock_settings)
            with patch(HTTPX) as mock_httpx:
                http = self._client_with(mock_httpx)

                await AffinitiesClient().check_registration()

                stale = AffinitiesClient._registration_cache
                stale["at"] -= AffinitiesClient.REGISTRATION_CACHE_SECONDS + 1

                await AffinitiesClient().check_registration()

        assert http.get.await_count == 2

    @pytest.mark.asyncio
    @patch(HTTPX)
    async def test_registering_a_dataset_is_never_served_from_the_cache(
        self, mock_httpx
    ):
        """The cache is for the readiness report, not for the write path."""
        fake = FakeAffinities(link_status=200)

        with patch(SETTINGS) as mock_settings:
            _configured_settings(mock_settings)
            _fake_httpx(mock_httpx, fake)

            await AffinitiesClient().register_dataset(title="One")
            await AffinitiesClient().register_dataset(title="Two")

        assert len([p for p in fake.paths if p.endswith("/datasets")]) == 2
