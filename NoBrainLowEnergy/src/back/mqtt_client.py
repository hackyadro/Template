from distance_model import Distance_model
import asyncio
import ssl
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from collections import deque
import os

import paho.mqtt.client as mqtt
from paho.mqtt.client import MQTTMessage

from models import ReceivedMQTTMessage, QoSLevel

# InfluxDB client
try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS
except Exception:  # Library may not be installed in some environments
    InfluxDBClient = None
    Point = None
    SYNCHRONOUS = None

logger = logging.getLogger(__name__)


class MQTTClient:
    """Async MQTT client with TLS support"""

    def __init__(
            self,
            broker_host: str,
            broker_port: int = 8883,
            username: Optional[str] = None,
            password: Optional[str] = None,
            client_id: Optional[str] = None,
            use_tls: bool = True,
            ca_cert_path: Optional[str] = None,
            cert_file_path: Optional[str] = None,
            key_file_path: Optional[str] = None,
            tls_insecure: bool = False
    ):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.client_id = client_id or os.getenv("MQTT_CLIENT_ID", "fastapi_backend")
        self.use_tls = use_tls
        self.ca_cert_path = ca_cert_path
        self.cert_file_path = cert_file_path
        self.key_file_path = key_file_path
        self.tls_insecure = tls_insecure
        self.distance_model = Distance_model()

        # InfluxDB settings (lazy init)
        self._influx_client = None
        self._influx_write_api = None
        self._influx_bucket = os.getenv("INFLUXDB_BUCKET")
        self._influx_org = os.getenv("INFLUXDB_ORG")
        self._influx_url = os.getenv("INFLUXDB_URL")
        self._influx_token = os.getenv("INFLUXDB_TOKEN")

        # Message storage
        self.recent_messages = deque(maxlen=1000)
        self.subscribed_topics = set()

        # Connection state
        self._connected = False
        self._client = None
        self._loop = None

        # Callbacks
        self.message_callbacks: Dict[str, Callable] = {}

    # -------- InfluxDB helpers --------
    def _ensure_influx(self):
        """Initialize InfluxDB client lazily using environment variables."""
        if self._influx_client or InfluxDBClient is None:
            return
        if not (self._influx_url and self._influx_token and self._influx_org and self._influx_bucket):
            logger.warning("InfluxDB not configured (missing env vars); skipping writes.")
            return
        try:
            self._influx_client = InfluxDBClient(url=self._influx_url, token=self._influx_token, org=self._influx_org)
            self._influx_write_api = self._influx_client.write_api(write_options=SYNCHRONOUS)
            logger.info("Initialized InfluxDB client")
        except Exception as e:
            logger.error(f"Failed to initialize InfluxDB client: {e}")
            self._influx_client = None
            self._influx_write_api = None

    def _write_position_to_influx(self, position: Any, topic: str, timestamp: datetime):
        """Write position data into InfluxDB as measurement 'position'.
        - If position is dict: write numeric items as fields.
        - If list/tuple: map to x,y,z if length is 2/3; otherwise f0, f1, ...
        - Otherwise: store as value (if numeric) or skip.
        """
        # Ensure client is ready
        if self._influx_write_api is None:
            self._ensure_influx()
        if self._influx_write_api is None:
            return  # Not configured or failed to init
        try:
            # Build point
            if Point is None:
                return
            point = Point("position").tag("topic", topic)

            # Use nanosecond precision timestamp
            point = point.time(timestamp)

            def _is_number(x):
                return isinstance(x, (int, float)) and not isinstance(x, bool)

            if isinstance(position, dict):
                wrote_any = False
                for k, v in position.items():
                    if _is_number(v):
                        point = point.field(str(k), float(v))
                        wrote_any = True
                if not wrote_any:
                    logger.debug("Position dict has no numeric fields; skipping write")
                    return
            elif isinstance(position, (list, tuple)):
                names = ["x", "y", "z"] if len(position) in (2, 3) else [f"f{i}" for i in range(len(position))]
                wrote_any = False
                for name, v in zip(names, position):
                    if _is_number(v):
                        point = point.field(name, float(v))
                        wrote_any = True
                if not wrote_any:
                    logger.debug("Position list has no numeric values; skipping write")
                    return
            else:
                if _is_number(position):
                    point = point.field("value", float(position))
                else:
                    logger.debug("Unsupported position type; skipping write")
                    return

            self._influx_write_api.write(bucket=self._influx_bucket, record=point)
        except Exception as e:
            logger.error(f"Failed to write position to InfluxDB: {e}")

    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self._connected and self._client and self._client.is_connected()

    async def connect(self) -> None:
        """Connect to MQTT broker"""
        try:
            self._loop = asyncio.get_event_loop()
            self._client = mqtt.Client(client_id=self.client_id)

            # Set up callbacks
            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect
            self._client.on_message = self._on_message
            self._client.on_publish = self._on_publish
            self._client.on_subscribe = self._on_subscribe
            self._client.on_log = self._on_log

            # Set up authentication
            if self.username and self.password:
                self._client.username_pw_set(self.username, self.password)

            # Set up TLS
            if self.use_tls:
                self._setup_tls()

            # Connect to broker
            logger.info(f"Connecting to MQTT broker at {self.broker_host}:{self.broker_port}")

            # Use async connection
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._client.connect,
                self.broker_host,
                self.broker_port,
                60
            )

        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise

    def _setup_tls(self) -> None:
        """Set up TLS configuration"""
        try:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)

            # Load CA certificate
            if self.ca_cert_path:
                context.load_verify_locations(self.ca_cert_path)

            # Load client certificate and key
            if self.cert_file_path and self.key_file_path:
                context.load_cert_chain(self.cert_file_path, self.key_file_path)

            # Configure certificate verification
            if self.tls_insecure:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            else:
                context.verify_mode = ssl.CERT_REQUIRED

            self._client.tls_set_context(context)
            logger.info("TLS configuration set up successfully")

        except Exception as e:
            logger.error(f"Failed to set up TLS: {e}")
            raise

    async def start(self) -> None:
        """Start the MQTT client loop"""
        if not self._client:
            raise RuntimeError("Client not initialized. Call connect() first.")

        try:
            # Start the network loop in a separate thread
            self._client.loop_start()
            logger.info("MQTT client loop started")

            # Keep the coroutine alive
            while True:
                await asyncio.sleep(1)
                if not self.is_connected():
                    logger.warning("MQTT connection lost, attempting to reconnect...")
                    try:
                        await self.connect()
                    except Exception as e:
                        logger.error(f"Reconnection failed: {e}")
                        await asyncio.sleep(5)  # Wait before retry

        except asyncio.CancelledError:
            logger.info("MQTT client loop cancelled")
            self._client.loop_stop()
            raise

    async def disconnect(self) -> None:
        """Disconnect from MQTT broker"""
        if self._client:
            self._client.loop_stop()
            await asyncio.get_event_loop().run_in_executor(
                None, self._client.disconnect
            )
            logger.info("Disconnected from MQTT broker")

    async def publish(
            self,
            topic: str,
            payload: Dict[str, Any],
            qos: QoSLevel = QoSLevel.AT_LEAST_ONCE,
            retain: bool = False
    ) -> None:
        """Publish a message to MQTT broker"""
        if not self.is_connected():
            raise RuntimeError("Not connected to MQTT broker")

        try:
            json_payload = json.dumps(payload, default=str)
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self._client.publish,
                topic,
                json_payload,
                qos.value,
                retain
            )

            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(f"Failed to publish message: {mqtt.error_string(result.rc)}")

            logger.info(f"Published message to topic: {topic}")

        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            raise

    async def subscribe(self, topic: str, qos: QoSLevel = QoSLevel.AT_LEAST_ONCE) -> None:
        """Subscribe to an MQTT topic"""
        if not self.is_connected():
            raise RuntimeError("Not connected to MQTT broker")

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self._client.subscribe,
                topic,
                qos.value
            )

            if result[0] != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(f"Failed to subscribe: {mqtt.error_string(result[0])}")

            self.subscribed_topics.add(topic)
            logger.info(f"Subscribed to topic: {topic}")
            print(f"Subscribed to topic: {topic}")

        except Exception as e:
            logger.error(f"Failed to subscribe to topic: {e}")
            raise

    async def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from an MQTT topic"""
        if not self.is_connected():
            raise RuntimeError("Not connected to MQTT broker")

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self._client.unsubscribe,
                topic
            )

            if result[0] != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(f"Failed to unsubscribe: {mqtt.error_string(result[0])}")

            self.subscribed_topics.discard(topic)
            logger.info(f"Unsubscribed from topic: {topic}")

        except Exception as e:
            logger.error(f"Failed to unsubscribe from topic: {e}")
            raise

    def get_recent_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent MQTT messages"""
        messages = list(self.recent_messages)[-limit:]
        return [msg.dict() for msg in messages]

    def add_message_callback(self, topic_pattern: str, callback: Callable) -> None:
        """Add a callback for messages on specific topic pattern"""
        self.message_callbacks[topic_pattern] = callback

    # Paho MQTT callbacks
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when client connects to broker"""
        if rc == 0:
            self._connected = True
            logger.info("Connected to MQTT broker successfully")

            # Resubscribe to topics
            for topic in self.subscribed_topics:
                client.subscribe(topic)

        else:
            self._connected = False
            logger.error(f"Failed to connect to MQTT broker: {mqtt.connack_string(rc)}")

    def _on_disconnect(self, client, userdata, rc):
        """Callback for when client disconnects from broker"""
        self._connected = False
        if rc != 0:
            logger.warning(f"Unexpected disconnection from MQTT broker: {mqtt.error_string(rc)}")
        else:
            logger.info("Disconnected from MQTT broker")

    def _on_message(self, client, userdata, msg: MQTTMessage):
        """Callback for when a message is received"""
        try:
            # Parse JSON payload
            payload = json.loads(msg.payload.decode())

            # Create message object
            received_msg = ReceivedMQTTMessage(
                topic=msg.topic,
                payload=payload,
                qos=msg.qos,
                retain=msg.retain,
                timestamp=datetime.utcnow()
            )

            # Store message
            self.recent_messages.append(received_msg)

            # Execute callbacks
            for pattern, callback in self.message_callbacks.items():
                if self._topic_matches(pattern, msg.topic):
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            asyncio.create_task(callback(received_msg))
                        else:
                            callback(received_msg)
                    except Exception as e:
                        logger.error(f"Error in message callback: {e}")

            positional_data = self.distance_model.Calc(received_msg)
            try:
                position = positional_data.get("position") if isinstance(positional_data, dict) else None
            except Exception:
                position = None
            if position is not None:
                self._write_position_to_influx(position, received_msg.topic, received_msg.timestamp)
            # Optionally forward to front-end if such integration exists
            try:
                front.send(positional_data)  # type: ignore[name-defined]
            except Exception:
                pass

            logger.debug(f"Received message on topic: {msg.topic}")
            print(f"Received message on topic LOL: {msg.payload}")

        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON payload from topic: {msg.topic}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _on_publish(self, client, userdata, mid):
        """Callback for when a message is published"""
        logger.debug(f"Message published with ID: {mid}")

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """Callback for when subscription is confirmed"""
        logger.debug(f"Subscription confirmed with ID: {mid}, QoS: {granted_qos}")

    def _on_log(self, client, userdata, level, buf):
        """Callback for MQTT client logging"""
        logger.debug(f"MQTT Log: {buf}")

    def _topic_matches(self, pattern: str, topic: str) -> bool:
        """Check if topic matches pattern (basic wildcard support)"""
        if pattern == topic:
            return True

        # Simple wildcard matching
        if '+' in pattern or '#' in pattern:
            pattern_parts = pattern.split('/')
            topic_parts = topic.split('/')

            if '#' in pattern:
                # Multi-level wildcard
                hash_index = pattern_parts.index('#')
                return pattern_parts[:hash_index] == topic_parts[:hash_index]

            if '+' in pattern:
                # Single-level wildcard
                if len(pattern_parts) != len(topic_parts):
                    return False

                for p_part, t_part in zip(pattern_parts, topic_parts):
                    if p_part != '+' and p_part != t_part:
                        return False
                return True

        return False
