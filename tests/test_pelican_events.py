"""Tests for Pelican file-event subscriptions (issue #262)."""

import asyncio
import json
from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.services.pelican_services.event_protocol import (
    Frame,
    escape_header,
    event_identity,
    is_heartbeat,
    parse_file_event,
    parse_frame,
    unescape_header,
    websocket_url,
)
from api.services.pelican_services.event_subscription import (
    DEFAULT_HEARTBEAT_MS,
    EventServerConfig,
    EventSubscriptionUnavailable,
    LISTENER_BUFFER,
    PelicanEventBroker,
    _Upstream,
    load_config,
)

CONFIG = EventServerConfig(
    url="wss://events.example/ws",
    client_id="ep-test",
    username="user",
    password="secret",
    virtual_host="playground",
    heartbeat_ms=10000,
)


def _event_body(**overrides):
    payload = {
        "name": "data.csv",
        "url": "pelican://osg-htc.org/public/data.csv",
        "size": 42,
        "mod_time": "2026-08-30T12:00:00Z",
    }
    payload.update(overrides)
    return json.dumps(payload)


class TestHeaderEscaping:
    """STOMP 1.2 header escaping."""

    def test_round_trip_covers_every_escape(self):
        """
        Every escaped character must survive a round trip. The four
        substitutions are easy to corrupt one at a time and the damage
        is invisible until the server rejects a frame.
        """
        raw = "a:b\nc\rd\\e"

        assert unescape_header(escape_header(raw)) == raw

    def test_escapes_use_the_spelling_the_protocol_requires(self):
        assert escape_header("a:b") == "a\\cb"
        assert escape_header("a\nb") == "a\\nb"
        assert escape_header("a\rb") == "a\\rb"
        assert escape_header("a\\b") == "a\\\\b"

    def test_backslash_is_escaped_first(self):
        """Otherwise the backslash pass would re-escape the others."""
        assert escape_header("\\n") == "\\\\n"
        assert unescape_header("\\\\n") == "\\n"


class TestFrames:
    """Frame encoding and parsing."""

    def test_encode_terminates_with_nul_after_a_blank_line(self):
        frame = Frame("CONNECT", {"accept-version": "1.2"}, "")

        assert frame.encode() == b"CONNECT\naccept-version:1.2\n\n\x00"

    def test_encode_parse_round_trip(self):
        frame = Frame("SEND", {"destination": "ep/osdf/pub"}, "body")

        parsed = parse_frame(frame.encode())

        assert parsed.command == "SEND"
        assert parsed.headers == {"destination": "ep/osdf/pub"}
        assert parsed.body == "body"

    def test_repeated_headers_keep_the_first_value(self):
        raw = b"MESSAGE\nid:first\nid:second\n\nbody\x00"

        assert parse_frame(raw).headers["id"] == "first"

    def test_parse_unescapes_headers(self):
        raw = b"MESSAGE\nkey:a\\cb\n\n\x00"

        assert parse_frame(raw).headers["key"] == "a:b"

    def test_heartbeat_recognition(self):
        assert is_heartbeat(b"\n") is True
        assert is_heartbeat(b"\r\n") is True
        assert is_heartbeat(b"MESSAGE\n\n\x00") is False


class TestWebsocketUrl:
    """URL normalisation."""

    @pytest.mark.parametrize(
        "given,expected",
        [
            ("https://a.example/ws", "wss://a.example/ws"),
            ("http://a.example/ws", "ws://a.example/ws"),
            ("wss://a.example/ws", "wss://a.example/ws"),
            ("ws://a.example/ws", "ws://a.example/ws"),
        ],
    )
    def test_scheme_is_mapped(self, given, expected):
        assert websocket_url(given) == expected

    @pytest.mark.parametrize("given", ["ftp://a.example", "not-a-url", ""])
    def test_unusable_url_is_rejected(self, given):
        with pytest.raises(ValueError):
            websocket_url(given)


class TestParseFileEvent:
    """The application-level event inside a MESSAGE body."""

    def test_valid_event(self):
        event = parse_file_event(_event_body(), "id-1", "ep/osdf/pub")

        assert event["name"] == "data.csv"
        assert event["size"] == 42
        assert event["event_id"] == "id-1"
        assert event["destination"] == "ep/osdf/pub"

    def test_json_string_envelope_is_unwrapped(self):
        """The publisher currently wraps the object in a JSON string."""
        event = parse_file_event(json.dumps(_event_body()))

        assert event["name"] == "data.csv"

    @pytest.mark.parametrize(
        "overrides",
        [
            {"name": ""},
            {"name": 5},
            {"url": ""},
            {"size": -1},
            {"size": "42"},
            {"size": True},
            {"mod_time": ""},
        ],
    )
    def test_malformed_event_is_rejected(self, overrides):
        with pytest.raises(ValueError):
            parse_file_event(_event_body(**overrides))

    def test_non_json_body_is_rejected(self):
        with pytest.raises(ValueError):
            parse_file_event("not json")

    def test_json_that_is_not_an_object_is_rejected(self):
        with pytest.raises(ValueError):
            parse_file_event("[1, 2, 3]")


class TestEventIdentity:
    """Redelivery identity."""

    def test_publisher_uuid_wins(self):
        frame = Frame(
            "MESSAGE",
            {"message-id": "m-1"},
            _event_body(uuid="u-1"),
        )

        assert event_identity(frame) == "u-1"

    def test_message_id_is_the_fallback(self):
        frame = Frame("MESSAGE", {"message-id": "m-1"}, _event_body())

        assert event_identity(frame) == "m-1"

    def test_unreadable_body_still_yields_an_identity(self):
        frame = Frame("MESSAGE", {}, "not json")

        assert event_identity(frame) == "unknown-message"


class TestCallerSuppliedCredentials:
    """A caller may bring its own identity and credentials."""

    @staticmethod
    def _env(**overrides):
        env = {
            "PELICAN_EVENT_CLIENT_ID": "ep-test",
            "PELICAN_EVENT_USERNAME": "ep-user",
            "PELICAN_EVENT_PASSWORD": "ep-secret",
        }
        env.update(overrides)
        return env

    def test_caller_values_win_over_the_endpoint(self):
        with patch.dict("os.environ", self._env(), clear=True):
            config = load_config(
                client_id="caller-1", username="mine", password="also-mine"
            )

        assert config.client_id == "caller-1"
        assert config.username == "mine"
        assert config.password == "also-mine"

    def test_omitted_values_fall_back_to_the_endpoint(self):
        """Callers without an account of their own still work."""
        with patch.dict("os.environ", self._env(), clear=True):
            config = load_config()

        assert config.client_id == "ep-test"
        assert config.username == "ep-user"

    def test_a_caller_id_alone_still_uses_endpoint_credentials(self):
        with patch.dict("os.environ", self._env(), clear=True):
            config = load_config(client_id="caller-1")

        assert config.client_id == "caller-1"
        assert config.username == "ep-user"

    def test_half_a_caller_credential_does_not_borrow_the_other_half(self):
        """
        Falling back per field would sign the caller in as the Endpoint
        under a name of their choosing, so the pair is taken together.
        """
        with patch.dict("os.environ", self._env(), clear=True):
            with pytest.raises(EventSubscriptionUnavailable) as exc:
                load_config(username="mine")

        assert "must be set together" in str(exc.value)

    def test_a_caller_id_with_a_slash_is_refused(self):
        with patch.dict("os.environ", self._env(), clear=True):
            with pytest.raises(EventSubscriptionUnavailable):
                load_config(client_id="a/b")

    def test_a_caller_id_lets_an_unconfigured_endpoint_serve(self):
        """An Endpoint with no event settings of its own still works."""
        with patch.dict("os.environ", {}, clear=True):
            config = load_config(
                client_id="caller-1", username="mine", password="also-mine"
            )

        assert config.client_id == "caller-1"


class TestLoadConfig:
    """Environment resolution."""

    @staticmethod
    def _env(**overrides):
        env = {
            "PELICAN_EVENT_CLIENT_ID": "ep-test",
            "PELICAN_EVENT_USERNAME": "user",
            "PELICAN_EVENT_PASSWORD": "secret",
        }
        env.update(overrides)
        return env

    def test_defaults(self):
        with patch.dict("os.environ", self._env(), clear=True):
            config = load_config()

        assert config.url.startswith("wss://")
        assert config.client_id == "ep-test"
        assert config.virtual_host == "playground"
        assert config.heartbeat_ms == DEFAULT_HEARTBEAT_MS

    def test_endpoint_uuid_is_the_fallback_client_id(self):
        """One less thing to configure, and unique per deployment."""
        env = {"AFFINITIES_EP_UUID": "uuid-1"}
        with patch.dict("os.environ", env, clear=True):
            assert load_config().client_id == "uuid-1"

    def test_missing_client_id_is_refused(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(EventSubscriptionUnavailable) as exc:
                load_config()

        assert "unique client id" in str(exc.value)

    def test_client_id_with_a_slash_is_refused(self):
        """It is one segment of the destination, so a slash reroutes it."""
        env = self._env(PELICAN_EVENT_CLIENT_ID="a/b")
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(EventSubscriptionUnavailable):
                load_config()

    def test_half_a_credential_is_refused(self):
        env = self._env(PELICAN_EVENT_PASSWORD="")
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(EventSubscriptionUnavailable):
                load_config()

    def test_unusable_server_url_is_refused(self):
        env = self._env(PELICAN_EVENT_SERVER_URL="ftp://nope")
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(EventSubscriptionUnavailable):
                load_config()

    @pytest.mark.parametrize("value", ["not-a-number", "0", "500"])
    def test_unusable_heartbeat_falls_back(self, value):
        """Settings allow extra keys, so a typo has to be caught here."""
        env = self._env(PELICAN_EVENT_HEARTBEAT_MS=value)
        with patch.dict("os.environ", env, clear=True):
            assert load_config().heartbeat_ms == DEFAULT_HEARTBEAT_MS

    def test_explicit_heartbeat_is_used(self):
        env = self._env(PELICAN_EVENT_HEARTBEAT_MS="30000")
        with patch.dict("os.environ", env, clear=True):
            assert load_config().heartbeat_ms == 30000


class TestUpstreamFrames:
    """The frames the Endpoint sends to the event server."""

    def test_destination_is_client_id_over_event_source(self):
        upstream = _Upstream("/osdf/vdc/public/", CONFIG)

        assert upstream.destination == "ep-test/osdf/vdc/public"

    def test_connect_frame(self):
        headers = _Upstream("osdf/pub", CONFIG)._connect_frame().headers

        assert headers["accept-version"] == "1.2"
        assert headers["host"] == "playground"
        assert headers["client-id"] == "ep-test"
        assert headers["heart-beat"] == "10000,10000"

    def test_subscribe_frame_acknowledges_individually(self):
        headers = _Upstream("osdf/pub", CONFIG)._subscribe_frame().headers

        assert headers["destination"] == "ep-test/osdf/pub"
        assert headers["ack"] == "client-individual"


class TestUpstreamFanOut:
    """Delivery to the listeners attached to one upstream."""

    @pytest.mark.asyncio
    async def test_every_listener_receives_every_event(self):
        """
        The whole point of sharing one upstream: listeners must not
        compete for events the way two STOMP clients on one id would.
        """
        upstream = _Upstream("osdf/pub", CONFIG)
        first = upstream.add_listener()
        second = upstream.add_listener()

        upstream._publish({"name": "a.csv"})

        assert first.get_nowait() == {"name": "a.csv"}
        assert second.get_nowait() == {"name": "a.csv"}

    @pytest.mark.asyncio
    async def test_slow_listener_drops_its_oldest_event(self):
        """A listener that stops reading must not grow without limit."""
        upstream = _Upstream("osdf/pub", CONFIG)
        queue = upstream.add_listener()
        for index in range(LISTENER_BUFFER):
            upstream._publish({"n": index})

        upstream._publish({"n": "newest"})

        assert queue.qsize() == LISTENER_BUFFER
        assert upstream.dropped == 1
        assert queue.get_nowait() == {"n": 1}

    @pytest.mark.asyncio
    async def test_removed_listener_stops_receiving(self):
        upstream = _Upstream("osdf/pub", CONFIG)
        queue = upstream.add_listener()
        upstream.remove_listener(queue)

        upstream._publish({"name": "a.csv"})

        assert queue.empty()

    def test_redelivery_is_suppressed(self):
        upstream = _Upstream("osdf/pub", CONFIG)

        assert upstream._already_seen("u-1") is False
        assert upstream._already_seen("u-1") is True

    def test_seen_identities_are_bounded(self):
        from api.services.pelican_services.event_subscription import (
            SEEN_EVENTS,
        )

        upstream = _Upstream("osdf/pub", CONFIG)
        for index in range(SEEN_EVENTS + 10):
            upstream._already_seen(f"u-{index}")

        assert len(upstream._seen) <= SEEN_EVENTS


class TestUpstreamMessages:
    """MESSAGE handling and acknowledgement."""

    @pytest.mark.asyncio
    async def test_event_is_published_and_acknowledged(self):
        upstream = _Upstream("osdf/pub", CONFIG)
        queue = upstream.add_listener()
        connection = AsyncMock()
        frame = Frame(
            "MESSAGE",
            {"ack": "a-1", "destination": "ep-test/osdf/pub"},
            _event_body(uuid="u-1"),
        )

        await upstream._on_message(connection, frame)

        assert queue.get_nowait()["name"] == "data.csv"
        connection.send.assert_awaited_once()
        assert b"ACK" in connection.send.await_args.args[0]

    @pytest.mark.asyncio
    async def test_duplicate_is_suppressed_but_still_acknowledged(self):
        """
        An unacknowledged message is redelivered forever, so a duplicate
        has to be acknowledged even though it is not published again.
        """
        upstream = _Upstream("osdf/pub", CONFIG)
        queue = upstream.add_listener()
        connection = AsyncMock()
        frame = Frame("MESSAGE", {"ack": "a-1"}, _event_body(uuid="u-1"))

        await upstream._on_message(connection, frame)
        await upstream._on_message(connection, frame)

        assert queue.qsize() == 1
        assert connection.send.await_count == 2

    @pytest.mark.asyncio
    async def test_unreadable_event_is_dropped_but_acknowledged(self):
        upstream = _Upstream("osdf/pub", CONFIG)
        queue = upstream.add_listener()
        connection = AsyncMock()
        frame = Frame("MESSAGE", {"ack": "a-1"}, "not json")

        await upstream._on_message(connection, frame)

        assert queue.empty()
        connection.send.assert_awaited_once()


class TestBroker:
    """One upstream per destination, reference counted."""

    @pytest.mark.asyncio
    async def test_two_listeners_on_one_identity_share_an_upstream(self):
        broker = PelicanEventBroker()
        with patch.object(_Upstream, "start"):
            first = broker.listen("osdf/pub", CONFIG)
            second = broker.listen("osdf/pub", CONFIG)
            task_a = asyncio.ensure_future(first.__anext__())
            task_b = asyncio.ensure_future(second.__anext__())
            await asyncio.sleep(0)

            assert len(broker._upstreams) == 1
            upstream = broker._upstreams["ep-test/osdf/pub"]
            assert len(upstream.listeners) == 2

            upstream._publish({"name": "a.csv"})
            assert await task_a == {"name": "a.csv"}
            assert await task_b == {"name": "a.csv"}

            await first.aclose()
            await second.aclose()

    @pytest.mark.asyncio
    async def test_a_caller_with_its_own_identity_gets_its_own_upstream(self):
        """
        Two identities cannot share one authenticated session, so the
        upstream is keyed by client id as well as event source.
        """
        other = replace(CONFIG, client_id="caller-1", username="other")
        broker = PelicanEventBroker()
        with patch.object(_Upstream, "start"):
            first = broker.listen("osdf/pub", CONFIG, idle_timeout=0.01)
            second = broker.listen("osdf/pub", other, idle_timeout=0.01)
            # A keepalive tick apiece registers both upstreams.
            assert await first.__anext__() is None
            assert await second.__anext__() is None

            assert set(broker._upstreams) == {
                "ep-test/osdf/pub",
                "caller-1/osdf/pub",
            }

            # An event on one identity must not reach the other.
            broker._upstreams["caller-1/osdf/pub"]._publish({"name": "a.csv"})
            assert await second.__anext__() == {"name": "a.csv"}
            assert await first.__anext__() is None

            await first.aclose()
            await second.aclose()

    @pytest.mark.asyncio
    async def test_upstream_is_dropped_when_the_last_listener_leaves(self):
        """An idle Endpoint should hold no connection to the server."""
        broker = PelicanEventBroker()
        with (
            patch.object(_Upstream, "start"),
            patch.object(_Upstream, "stop", new=AsyncMock()),
        ):
            stream = broker.listen("osdf/pub", CONFIG, idle_timeout=0.01)
            # One keepalive tick is enough to get the upstream registered.
            assert await stream.__anext__() is None
            assert len(broker._upstreams) == 1

            await stream.aclose()

        assert broker._upstreams == {}

    @pytest.mark.asyncio
    async def test_idle_stream_yields_none_for_a_keepalive(self):
        """
        The wait has to time out inside the generator: cancelling an
        __anext__ from outside would unwind it and tear the
        subscription down on every quiet interval.
        """
        broker = PelicanEventBroker()
        with patch.object(_Upstream, "start"):
            stream = broker.listen("osdf/pub", CONFIG, idle_timeout=0.01)

            assert await stream.__anext__() is None

            upstream = broker._upstreams["ep-test/osdf/pub"]
            upstream._publish({"name": "a.csv"})
            assert await stream.__anext__() == {"name": "a.csv"}

            await stream.aclose()

    @pytest.mark.asyncio
    async def test_empty_event_source_is_refused(self):
        broker = PelicanEventBroker()
        with pytest.raises(EventSubscriptionUnavailable):
            await broker.listen("  /  ", CONFIG).__anext__()

    def test_status_reports_each_upstream(self):
        broker = PelicanEventBroker()
        broker._upstreams["ep-test/osdf/pub"] = _Upstream("osdf/pub", CONFIG)

        status = broker.status()["ep-test/osdf/pub"]

        assert status["event_source"] == "osdf/pub"
        assert status["client_id"] == "ep-test"
        assert status["listeners"] == 0

    def test_status_never_reports_a_credential(self):
        """
        Any viewer on the Endpoint can read this route, so it must not
        echo back a password another caller supplied.
        """
        broker = PelicanEventBroker()
        broker._upstreams["ep-test/osdf/pub"] = _Upstream("osdf/pub", CONFIG)

        rendered = json.dumps(broker.status())

        assert CONFIG.password not in rendered
        assert CONFIG.username not in rendered
        assert broker.status()["ep-test/osdf/pub"]["authenticated"] is True


class TestSubscribeRoute:
    """GET /pelican/subscribe and /pelican/subscriptions."""

    @staticmethod
    def _client():
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from api.routes.pelican_routes import router

        app = FastAPI()
        app.include_router(router)
        return app, TestClient(app)

    @staticmethod
    def _as(roles):
        return lambda: {
            "roles": roles,
            "groups": [],
            "sub": "test_user",
            "username": "Test User",
        }

    def test_requires_authentication(self):
        """The stream inherits the router gate added for issue #261."""
        _app, client = self._client()

        response = client.get("/pelican/subscribe", params={"event_source": "osdf/pub"})

        assert response.status_code == 401

    def _subscribe(self, params=None, headers=None):
        """Call the route as a viewer, returning the response."""
        from api.services.auth_services import get_current_user

        app, client = self._client()
        app.dependency_overrides[get_current_user] = self._as(["ndp_viewer"])
        try:
            return client.get(
                "/pelican/subscribe",
                params={"event_source": "osdf/pub", **(params or {})},
                headers=headers or {},
            )
        finally:
            app.dependency_overrides.clear()

    @patch("api.routes.pelican_routes.broker")
    @patch("api.routes.pelican_routes.load_config")
    def test_credentials_are_accepted_as_query_parameters(
        self, mock_config, mock_broker
    ):
        mock_config.return_value = CONFIG

        async def fake_listen(event_source, config, *args, **kwargs):
            yield None

        mock_broker.listen = fake_listen

        self._subscribe(
            {
                "client_id": "caller-1",
                "username": "mine",
                "password": "also-mine",
            }
        )

        mock_config.assert_called_once_with(
            client_id="caller-1", username="mine", password="also-mine"
        )

    @patch("api.routes.pelican_routes.broker")
    @patch("api.routes.pelican_routes.load_config")
    def test_headers_win_over_query_parameters(self, mock_config, mock_broker):
        """
        A query string is written to the access log, so the header is
        the safer way to pass a password and has to take precedence.
        """
        mock_config.return_value = CONFIG

        async def fake_listen(event_source, config, *args, **kwargs):
            yield None

        mock_broker.listen = fake_listen

        self._subscribe(
            {"client_id": "from-query", "username": "q", "password": "q-pass"},
            {
                "X-Pelican-Event-Client-Id": "from-header",
                "X-Pelican-Event-Username": "h",
                "X-Pelican-Event-Password": "h-pass",
            },
        )

        mock_config.assert_called_once_with(
            client_id="from-header", username="h", password="h-pass"
        )

    @patch("api.routes.pelican_routes.broker")
    @patch("api.routes.pelican_routes.load_config")
    def test_nothing_supplied_falls_back_to_the_endpoint(
        self, mock_config, mock_broker
    ):
        mock_config.return_value = CONFIG

        async def fake_listen(event_source, config, *args, **kwargs):
            yield None

        mock_broker.listen = fake_listen

        self._subscribe()

        mock_config.assert_called_once_with(
            client_id=None, username=None, password=None
        )

    @patch("api.routes.pelican_routes.load_config")
    def test_a_rejected_credential_is_reported_not_swallowed(self, mock_config):
        mock_config.side_effect = EventSubscriptionUnavailable(
            "The username and password must be set together."
        )

        response = self._subscribe({"username": "mine"})

        assert response.status_code == 503
        assert "set together" in response.json()["detail"]

    @patch("api.routes.pelican_routes.load_config")
    def test_unconfigured_endpoint_reports_unavailable(self, mock_config):
        mock_config.side_effect = EventSubscriptionUnavailable("no client id")
        from api.services.auth_services import get_current_user

        app, client = self._client()
        app.dependency_overrides[get_current_user] = self._as(["ndp_viewer"])
        try:
            response = client.get(
                "/pelican/subscribe", params={"event_source": "osdf/pub"}
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 503
        assert response.json()["detail"] == "no client id"

    @patch("api.routes.pelican_routes.broker")
    @patch("api.routes.pelican_routes.load_config")
    def test_stream_emits_events_and_keepalives(self, mock_config, mock_broker):
        mock_config.return_value = CONFIG

        async def fake_listen(event_source, config, *args, **kwargs):
            yield None
            yield {"name": "a.csv", "url": "pelican://x/a.csv"}

        mock_broker.listen = fake_listen
        from api.services.auth_services import get_current_user

        app, client = self._client()
        app.dependency_overrides[get_current_user] = self._as(["ndp_viewer"])
        try:
            response = client.get(
                "/pelican/subscribe", params={"event_source": "osdf/pub"}
            )
        finally:
            app.dependency_overrides.clear()

        body = response.text
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert ": subscribed" in body
        assert ": keepalive" in body
        assert "event: file" in body
        assert '"name": "a.csv"' in body

    @patch("api.routes.pelican_routes.broker")
    def test_subscriptions_lists_upstream_state(self, mock_broker):
        mock_broker.status = MagicMock(
            return_value={"osdf/pub": {"state": "connected", "listeners": 2}}
        )
        from api.services.auth_services import get_current_user

        app, client = self._client()
        app.dependency_overrides[get_current_user] = self._as(["ndp_viewer"])
        try:
            response = client.get("/pelican/subscriptions")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["subscriptions"]["osdf/pub"]["listeners"] == 2
