# NoBrainLowEnergy FastAPI Backend

## Prerequisites

- Python 3.8 or higher
- OpenSSL (for certificate generation)

## Instruction

1) python3 NoBrainLowEnergy/src/back/generate_certs.py
2) mv Template/certs/* NoBrainLowEnergy/src/back/certs
3) docker-compose -f NoBrainLowEnergy/src/back/docker-compose.yml up -d --build 


## Docs

The API will be available at:
- HTTP: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

## Configuration

### Environment Variables in docker - main source of configuration

```env
      - DOCKER_INFLUXDB_INIT_MODE=setup
      - DOCKER_INFLUXDB_INIT_USERNAME=admin
      - DOCKER_INFLUXDB_INIT_PASSWORD=adminadmin
      - DOCKER_INFLUXDB_INIT_ORG=nobrain
      - DOCKER_INFLUXDB_INIT_BUCKET=default
      - DOCKER_INFLUXDB_INIT_RETENTION=0
      - DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=${INFLUXDB_TOKEN:-admintoken}
      - MQTT_BROKER_HOST=mosquitto
      - MQTT_BROKER_PORT=1883
      - MQTT_BROKER_PORT_SAFE=8883
      - MQTT_USE_TLS=false
      - MQTT_CA_CERT_PATH=/app/certs/ca.crt
      - MQTT_CERT_FILE_PATH=/app/certs/client.crt
      - MQTT_KEY_FILE_PATH=/app/certs/client.key
      - MQTT_CLIENT_ID=nobrainlowenergy-backend
      - MQTT_USERNAME=your_mqtt_username
      - FASTAPI_TLS_ON=false
      - MQTT_AUTO_SUBSCRIBE_TOPICS=devices/+/beacons
      - INFLUXDB_URL=http://influxdb:8086
      - INFLUXDB_TOKEN=${INFLUXDB_TOKEN:-admintoken}
      - INFLUXDB_ORG=nobrain
      - INFLUXDB_BUCKET=default
      - SSL_KEY_FILE=/app/certs/server.key
      - SSL_CERT_FILE=/app/certs/server.crt
```
