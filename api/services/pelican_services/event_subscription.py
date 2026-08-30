# api/services/pelican_services/event_subscription.py
"""
Fan-out of Pelican file events to Server-Sent Events listeners.

The event server hands every subscription a ``client-id`` that must be
unique: two connections sharing one compete for the same events instead
of both receiving them. A subscription per SSE caller would therefore
either need a fresh identity each time — leaving orphaned client ids
registered upstream — or silently split the stream between callers.

So the Endpoint holds **one** upstream subscription per event source,
under its own stable client id, and fans each event out to every SSE
listener attached to that source. The upstream connection is opened when
the first listener arrives and closed when the last one leaves.
"""

import asyncio
import base64
import inspect
import logging
import os
from collections import OrderedDict
from dataclasses import dataclass
from typing import AsyncIterator, Dict, Optional, Set

from api.services.pelican_services.event_protocol import (
    Frame,
    event_identity,
    is_heartbeat,
    parse_file_event,
    parse_frame,
    websocket_url,
)

try:  # pragma: no cover - absence is covered by load_config's guard
    import websockets
except ImportError:  # pragma: no cover
    websockets = None

logger = logging.getLogger(__name__)

DEFAULT_EVENT_SERVER = "https://stomp-server.chtcdev.chtc.io/ws"
DEFAULT_VIRTUAL_HOST = "playground"
DEFAULT_HEARTBEAT_MS = 10000
MAX_BACKOFF_SECONDS = 30

# Per-listener buffer. Bounded, unlike the client library's: a browser
# tab that stops reading must not be able to grow the Endpoint's memory
# without limit. When it fills, the oldest event is dropped and counted.
LISTENER_BUFFER = 256

# How many event identities to remember for redelivery suppression. The
# server may redeliver after a reconnect; without this every listener
# would see the same event twice.
SEEN_EVENTS = 2048

# Silence after which a listener is handed a keepalive. Without one, an
# idle stream looks dead to proxies and they close it.
IDLE_TIMEOUT_SECONDS = 15.0


class EventSubscriptionUnavailable(RuntimeError):
    """The subscription cannot be served with the current configuration."""


@dataclass(frozen=True)
class EventServerConfig:
    """Connection settings for the event server."""

    url: str
    client_id: str
    username: str
    password: str
    virtual_host: str
    heartbeat_ms: int


def load_config() -> EventServerConfig:
    """
    Read the event server settings from the environment.

    Returns
    -------
    EventServerConfig
        Validated settings.

    Raises
    ------
    EventSubscriptionUnavailable
        If a required setting is missing or unusable. Settings are
        declared with ``extra: "allow"``, so a typo would otherwise
        surface as a failed connection instead of a clear error.
    """
    if websockets is None:
        raise EventSubscriptionUnavailable(
            "The 'websockets' package is required for Pelican event "
            "subscriptions and is not installed."
        )

    raw_url = os.getenv("PELICAN_EVENT_SERVER_URL") or DEFAULT_EVENT_SERVER
    try:
        url = websocket_url(raw_url)
    except ValueError as exc:
        raise EventSubscriptionUnavailable(str(exc)) from exc

    # A stable identity per Endpoint. Falling back to the Endpoint UUID
    # keeps it unique across deployments without another thing to set.
    client_id = (
        os.getenv("PELICAN_EVENT_CLIENT_ID") or os.getenv("AFFINITIES_EP_UUID") or ""
    ).strip()
    if not client_id:
        raise EventSubscriptionUnavailable(
            "PELICAN_EVENT_CLIENT_ID is not set and no Endpoint UUID is "
            "available to derive it from. The event server requires a "
            "unique client id per subscriber."
        )
    if "/" in client_id:
        raise EventSubscriptionUnavailable(
            "PELICAN_EVENT_CLIENT_ID must not contain '/': it is one "
            "segment of the STOMP destination."
        )

    username = os.getenv("PELICAN_EVENT_USERNAME", "")
    password = os.getenv("PELICAN_EVENT_PASSWORD", "")
    if bool(username) != bool(password):
        raise EventSubscriptionUnavailable(
            "PELICAN_EVENT_USERNAME and PELICAN_EVENT_PASSWORD must be " "set together."
        )

    return EventServerConfig(
        url=url,
        client_id=client_id,
        username=username,
        password=password,
        virtual_host=os.getenv("PELICAN_EVENT_VIRTUAL_HOST", DEFAULT_VIRTUAL_HOST),
        heartbeat_ms=_heartbeat_ms(),
    )


def _heartbeat_ms() -> int:
    """Resolve the liveness interval, falling back on an unusable value."""
    raw = os.getenv("PELICAN_EVENT_HEARTBEAT_MS", "")
    if not raw:
        return DEFAULT_HEARTBEAT_MS
    try:
        value = int(raw)
    except ValueError:
        logger.warning(
            f"PELICAN_EVENT_HEARTBEAT_MS is not an integer ({raw!r}); "
            f"using {DEFAULT_HEARTBEAT_MS}."
        )
        return DEFAULT_HEARTBEAT_MS
    if value < 1000:
        logger.warning(
            f"PELICAN_EVENT_HEARTBEAT_MS must be at least 1000 (got "
            f"{value}); using {DEFAULT_HEARTBEAT_MS}."
        )
        return DEFAULT_HEARTBEAT_MS
    return value


def _basic_auth(username: str, password: str) -> str:
    """Build the Basic credential for the WebSocket handshake."""
    raw = f"{username}:{password}".encode()
    return f"Basic {base64.b64encode(raw).decode()}"


def _header_kwargs(headers: Optional[Dict[str, str]]) -> Dict[str, object]:
    """Name the handshake-header argument the way this websockets wants it."""
    if not headers:
        return {}
    parameters = inspect.signature(websockets.connect).parameters
    if "additional_headers" in parameters:
        return {"additional_headers": headers}
    return {"extra_headers": headers}


class _Upstream:
    """One STOMP subscription, shared by every listener on an event source."""

    def __init__(self, event_source: str, config: EventServerConfig):
        self.event_source = event_source.strip().strip("/")
        self.config = config
        self.listeners: Set[asyncio.Queue] = set()
        self.state = "starting"
        self.last_error = ""
        self.dropped = 0
        self._seen: "OrderedDict[str, None]" = OrderedDict()
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()

    @property
    def destination(self) -> str:
        """The STOMP destination this subscription listens on."""
        return f"{self.config.client_id}/{self.event_source}"

    def start(self) -> None:
        """Begin connecting, without blocking the caller."""
        if self._task is None:
            self._task = asyncio.ensure_future(self._run())

    async def stop(self) -> None:
        """Close the upstream connection and wait for the task to end."""
        self._stop.set()
        task = self._task
        self._task = None
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug(f"Upstream task ended with {exc}")

    def add_listener(self) -> asyncio.Queue:
        """Attach a listener and hand back the queue it should read."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=LISTENER_BUFFER)
        self.listeners.add(queue)
        return queue

    def remove_listener(self, queue: asyncio.Queue) -> None:
        """Detach a listener that has gone away."""
        self.listeners.discard(queue)

    def _already_seen(self, identity: str) -> bool:
        """Suppress a redelivery, remembering a bounded number of ids."""
        if identity in self._seen:
            return True
        self._seen[identity] = None
        while len(self._seen) > SEEN_EVENTS:
            self._seen.popitem(last=False)
        return False

    def _publish(self, payload: dict) -> None:
        """Hand an event to every listener, dropping the oldest if full."""
        for queue in list(self.listeners):
            if queue.full():
                try:
                    queue.get_nowait()
                    self.dropped += 1
                except asyncio.QueueEmpty:  # pragma: no cover - race only
                    pass
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:  # pragma: no cover - race only
                self.dropped += 1

    async def _run(self) -> None:
        """Keep the upstream connected, backing off after a failure."""
        delay = 1.0
        while not self._stop.is_set():
            try:
                await self._session()
                delay = 1.0
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.state = "disconnected"
                self.last_error = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    f"Pelican event subscription to {self.destination} "
                    f"failed ({self.last_error}); retrying in {delay:.0f}s."
                )
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=delay)
                except asyncio.TimeoutError:
                    pass
                delay = min(delay * 2, MAX_BACKOFF_SECONDS)

    async def _session(self) -> None:
        """Run one connection, from handshake until it drops."""
        headers = None
        if self.config.username:
            headers = {
                "Authorization": _basic_auth(self.config.username, self.config.password)
            }

        self.state = "connecting"
        # Our own heartbeat below is the liveness signal, so the
        # websockets keepalive would only duplicate it.
        connect = websockets.connect(
            self.config.url, ping_interval=None, **_header_kwargs(headers)
        )
        async with connect as connection:
            await connection.send(self._connect_frame().encode())

            greeting = await self._receive(connection)
            if greeting.command != "CONNECTED":
                raise RuntimeError(
                    f"Expected CONNECTED from the event server, got "
                    f"{greeting.command or 'nothing'}."
                )

            await connection.send(self._subscribe_frame().encode())
            self.state = "connected"
            self.last_error = ""
            logger.info(f"Subscribed to {self.destination} as {self.config.client_id}")

            heartbeat = asyncio.ensure_future(self._heartbeat(connection))
            try:
                while not self._stop.is_set():
                    frame = await self._receive(connection)
                    if frame.command == "MESSAGE":
                        await self._on_message(connection, frame)
                    elif frame.command == "ERROR":
                        message = frame.body or frame.headers.get(
                            "message", "server error"
                        )
                        self.last_error = f"Server error: {message}"
                        logger.error(f"Event server reported an error: {message}")
            finally:
                heartbeat.cancel()
                self.state = "disconnected"

    def _connect_frame(self) -> Frame:
        return Frame(
            "CONNECT",
            {
                "accept-version": "1.2",
                "host": self.config.virtual_host,
                "client-id": self.config.client_id,
                "heart-beat": (
                    f"{self.config.heartbeat_ms},{self.config.heartbeat_ms}"
                ),
            },
        )

    def _subscribe_frame(self) -> Frame:
        return Frame(
            "SUBSCRIBE",
            {
                "id": self.config.client_id,
                "subscription": self.config.client_id,
                "destination": self.destination,
                "ack": "client-individual",
            },
        )

    async def _heartbeat(self, connection) -> None:
        """
        Send the heartbeats promised in CONNECT.

        At half the negotiated interval, so an ordinary scheduling delay
        is not read by the server as a dead client.
        """
        interval = self.config.heartbeat_ms / 2000
        while True:
            await asyncio.sleep(interval)
            await connection.send(b"\n")

    async def _receive(self, connection) -> Frame:
        """Read the next frame, skipping heartbeats."""
        while True:
            data = await connection.recv()
            if isinstance(data, str):
                data = data.encode()
            if is_heartbeat(data):
                continue
            return parse_frame(data)

    async def _on_message(self, connection, frame: Frame) -> None:
        """Publish a MESSAGE to the listeners and acknowledge it."""
        identity = event_identity(frame)
        destination = frame.headers.get("destination", "")

        if not self._already_seen(identity):
            try:
                payload = parse_file_event(frame.body, identity, destination)
            except ValueError as exc:
                logger.warning(f"Ignoring unreadable event: {exc}")
            else:
                self._publish(payload)

        # Acknowledged even when unreadable or a duplicate: leaving it
        # unacknowledged would have the server redeliver it forever.
        ack_id = frame.headers.get("ack")
        if ack_id:
            await connection.send(Frame("ACK", {"id": ack_id}).encode())


class PelicanEventBroker:
    """Holds one :class:`_Upstream` per event source, reference counted."""

    def __init__(self) -> None:
        self._upstreams: Dict[str, _Upstream] = {}
        self._lock = asyncio.Lock()

    def status(self) -> Dict[str, dict]:
        """Report what is currently subscribed, for diagnostics."""
        return {
            source: {
                "state": upstream.state,
                "destination": upstream.destination,
                "listeners": len(upstream.listeners),
                "dropped_events": upstream.dropped,
                "last_error": upstream.last_error,
            }
            for source, upstream in self._upstreams.items()
        }

    async def listen(
        self,
        event_source: str,
        config: EventServerConfig,
        idle_timeout: float = IDLE_TIMEOUT_SECONDS,
    ) -> AsyncIterator[Optional[dict]]:
        """
        Yield events for ``event_source`` until the caller goes away.

        Opens the upstream subscription on the first listener and closes
        it when the last one leaves, so an idle Endpoint holds no
        connection to the event server.

        Yields ``None`` once ``idle_timeout`` passes with no event, so
        the caller can emit a keepalive. The wait is timed out *here*
        rather than around the iterator, because cancelling an
        ``__anext__`` would unwind this generator and tear the
        subscription down on every quiet interval.

        Parameters
        ----------
        event_source : str
            Namespace to watch, e.g. ``osdf/vdc/public/data``.
        config : EventServerConfig
            Settings for the upstream connection.
        idle_timeout : float
            Seconds of silence before yielding ``None``.

        Raises
        ------
        EventSubscriptionUnavailable
            If ``event_source`` is empty.
        """
        source = event_source.strip().strip("/")
        if not source:
            raise EventSubscriptionUnavailable(
                "event_source must be a non-empty namespace path."
            )

        async with self._lock:
            upstream = self._upstreams.get(source)
            if upstream is None:
                upstream = _Upstream(source, config)
                self._upstreams[source] = upstream
                upstream.start()
            queue = upstream.add_listener()

        try:
            while True:
                try:
                    yield await asyncio.wait_for(queue.get(), timeout=idle_timeout)
                except asyncio.TimeoutError:
                    yield None
        finally:
            async with self._lock:
                upstream.remove_listener(queue)
                if not upstream.listeners:
                    self._upstreams.pop(source, None)
                    await upstream.stop()


#: Process-wide broker. One per worker, which is what keeps the client
#: id unique: two workers would otherwise share it and split the stream.
broker = PelicanEventBroker()
