# NoBrainLowEnergy FastAPI Backend

<!-- ## Features

- **FastAPI Framework**: Modern, fast, and async web framework
- **MQTT Integration**: Secure communication with MQTT broker using TLS
- **RESTful API**: Complete REST API for device management and IoT operations
- **TLS/SSL Support**: End-to-end encryption for both HTTP and MQTT connections
- **Auto-generated Documentation**: Interactive API docs with Swagger UI
- **Docker Support**: Containerized deployment with Docker Compose
- **Async Architecture**: High-performance asynchronous operations
- **Type Safety**: Full type hints and Pydantic models for data validation -->

## Quick Start

### Prerequisites

- Python 3.8 or higher
- OpenSSL (for certificate generation)
- MQTT Broker Mosquitto

### Installation

1. **Clone and navigate to the backend directory:**
   ```bash
   cd NoBrainLowEnergy/src/back
   ```

2. **Install dependencies:**
   ```bash
   python run.py --install-deps
   ```

3. **Generate TLS certificates:**
   ```bash
   python run.py --generate-certs
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the server:**
   ```bash
   python run.py
   ```

The API will be available at:
- HTTPS: `https://localhost:8000`
- HTTP: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

## Configuration

### Environment Variables

Edit the `.env` file to configure your backend:

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

# MQTT Broker Configuration
MQTT_BROKER_HOST=mosquitto
MQTT_BROKER_PORT=1883
MQTT_USERNAME=your_mqtt_username
MQTT_PASSWORD=your_mqtt_password
MQTT_CLIENT_ID=fastapi_backend

# TLS Configuration
MQTT_USE_TLS=False
MQTT_CA_CERT_PATH=certs/ca.crt
MQTT_CERT_FILE_PATH=certs/client.crt
MQTT_KEY_FILE_PATH=certs/client.key
```

> **Note:**  
> - When running with Docker Compose, the MQTT broker host should be `mosquitto` and port `1883` (no TLS by default).
> - If you enable TLS, set `MQTT_USE_TLS=True` and adjust the port and certificate paths as needed.

### MQTT Broker Setup

#### Using Mosquitto

1. **Install Mosquitto:**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install mosquitto mosquitto-clients
   
   # Windows (using Chocolatey)
   choco install mosquitto
   
   # macOS (using Homebrew)
   brew install mosquitto
   ```

2. **Use the generated configuration:**
   ```bash
   mosquitto -c mosquitto.conf
   ```

3. **Test the connection:**
   ```bash
   # Subscribe to test topic (no TLS)
   mosquitto_sub -h mosquitto -p 1883 -t "test/topic"

   # Publish test message (no TLS)
   mosquitto_pub -h mosquitto -p 1883 -t "test/topic" -m "Hello MQTT!"

   # If using TLS, add --cafile, --cert, and --key options and use the correct port
   ```

## API Endpoints

### Core Endpoints

- `GET /` - Root endpoint with server info
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation

### MQTT Endpoints

- `POST /mqtt/publish` - Publish message to MQTT topic
- `POST /mqtt/subscribe` - Subscribe to MQTT topic
- `GET /mqtt/messages` - Get recent MQTT messages

### Device Management

- `GET /api/v1/devices` - List all devices (with pagination)
- `GET /api/v1/devices/{device_id}` - Get specific device
- `POST /api/v1/devices/{device_id}/command` - Send command to device
- `GET /api/v1/devices/{device_id}/sensor-data` - Get sensor data

### System Management

- `GET /api/v1/system/status` - Get system status
- `GET /api/v1/alerts` - Get system alerts
- `POST /api/v1/alerts/{alert_id}/acknowledge` - Acknowledge alert

## Data Models

### MQTT Message
```json
{
  "topic": "nobrainlowenergy/devices/sensor_001/data",
  "payload": {
    "temperature": 23.5,
    "humidity": 60.2,
    "timestamp": "2025-01-01T12:00:00Z"
  },
  "qos": 1,
  "retain": false
}
```

### Device Status
```json
{
  "device_id": "sensor_001",
  "device_type": "sensor",
  "status": "online",
  "last_seen": "2025-01-01T12:00:00Z",
  "battery_level": 85.5,
  "firmware_version": "1.2.3"
}
```

### Device Command
```json
{
  "command_id": "cmd_001",
  "device_id": "actuator_001",
  "command": "set_temperature",
  "parameters": {
    "target_temp": 22.0
  },
  "priority": 1
}
```

## Docker Deployment

### Using Docker Compose

1. **Build and start services:**
   ```bash
   docker-compose up -d
   ```

   This will start the FastAPI backend and Mosquitto MQTT broker with the correct networking for service discovery.

2. **View logs:**
   ```bash
   docker-compose logs -f
   ```

3. **Stop services:**
   ```bash
   docker-compose down
   ```

### Services Included

- **FastAPI Backend**: Main API server
- **Mosquitto MQTT**: MQTT broker (default port 1883, no TLS)
- **Redis**: Caching and session storage (optional)
- **PostgreSQL**: Database for persistent storage (optional)

## Development

### Running in Development Mode

```bash
# Install development dependencies
pip install -r requirements.txt

# Run with auto-reload
python run.py --host 127.0.0.1 --port 8000

# Or use uvicorn directly
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

### Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=.
```

## Security

### TLS Configuration

- **MQTT TLS**: Uses mutual TLS authentication with client certificates
- **API TLS**: Optional HTTPS support for API endpoints
- **Certificate Management**: Automated certificate generation for development

### Best Practices

1. **Change default passwords** in production
2. **Use proper CA certificates** instead of self-signed for production
3. **Enable authentication** on MQTT broker
4. **Implement proper ACLs** for MQTT topics
5. **Use environment variables** for sensitive configuration

## Monitoring and Logging

### Health Checks

The `/health` endpoint provides system status:
```json
{
  "status": "healthy",
  "mqtt_status": "connected",
  "timestamp": "2025-01-01T12:00:00Z"
}
```

### Logging

Logs are configured with structured logging:
- **Console output**: Development mode
- **File output**: Production mode (logs/ directory)
- **Log levels**: INFO, DEBUG, WARNING, ERROR

## Troubleshooting

### Common Issues

1. **MQTT Connection Failed**
   - Make sure the broker host and port match your environment (`mosquitto:1883` for Docker Compose).
   - If using TLS, ensure `MQTT_USE_TLS=True` and the correct port/certificates.
   - Check broker is running: `docker-compose ps` or `netstat -an | grep 1883`
   - Verify certificates if using TLS: `openssl verify -CAfile certs/ca.crt certs/client.crt`
   - Check firewall settings

2. **Certificate Errors**
   - Regenerate certificates: `python generate_certs.py`
   - Check file permissions: `ls -la certs/`
   - Verify paths in configuration

3. **Import Errors**
   - Install dependencies: `python run.py --install-deps`
   - Check Python version: `python --version`
   - Verify virtual environment activation

### Debug Mode

Enable debug logging by setting `LOG_LEVEL=DEBUG` in `.env` file.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Check the [troubleshooting section](#troubleshooting)
- Open an issue on GitHub
- Review the API documentation at `/docs`