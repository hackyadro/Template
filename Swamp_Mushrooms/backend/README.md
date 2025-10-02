# build & run
docker compose up --build

# FastAPI will be at http://localhost:8000
# Health: http://localhost:8000/health
# Beacons: http://localhost:8000/beacons
# Tracks: http://localhost:8000/tracks/{device_id}

# To test MQTT publish:
mosquitto_pub -h localhost -p 1883 -t "hackyadro/YOUR_TEAM_NAME/anchors/measurement" -m '{"device_id":"esp01","scan":[{"beacon_id":"beacon_1","rssi":-60},{"beacon_id":"beacon_2","rssi":-70},{"beacon_id":"beacon_3","rssi":-65}],"timestamp_us":1696212345678900}'
