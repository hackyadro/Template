# build & run
docker compose up --build

# FastAPI will be at http://localhost:8000
# Health: http://localhost:8000/health
# Beacons: http://localhost:8000/beacons
# Tracks: http://localhost:8000/tracks/{device_id}

# To test MQTT publish:
mosquitto_pub -h localhost -p 1883 -t "hackyadro/Swamp_Mushrooms/anchors/test_anchor/measurement" -f example/payload.json 