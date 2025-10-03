package main

import (
	"log/slog"
	"os"
	m "service/internal/mosquitto"
	"service/internal/position"
	"service/internal/recorder"
	"service/internal/storage"
	"time"
)

func main() {
	// Настройка логгера
	log := setupLogger()

	beaconCoords := map[string][2]float64{
		"beacon_1": {0, 0},
		"beacon_2": {2, 0},
		"beacon_3": {4, 0},
		"beacon_4": {0, 2},
		"beacon_5": {4, 2},
		"beacon_6": {0, 4},
		"beacon_7": {2, 4},
		"beacon_8": {4, 4},
	}

	storage := storage.NewStorage()
	ps := position.NewPositionService(storage, beaconCoords)

	// Создание клиента для MQTT брокера, по сути это как консьюмер для кафки
	var cfg m.Config
	cfg.Broker = "mosquitto:" + os.Getenv("MOSQUITTO_INTERNAL_PORT")
	cfg.ClientId = "service"
	cfg.Username = os.Getenv("MOSQUITTO_USER")
	cfg.Password = os.Getenv("MOSQUITTO_PASSWORD")
	cfg.Topics = []string{os.Getenv("MOSQUITTO_TOPIC")}
	handler := m.NewHandler(storage, log)
	_, err := m.NewClient(cfg, handler, storage, log)
	if err != nil {
		log.Error("creating broker client error", slog.Any("error: %w", err))
	}
	log.Info("service connected to broker")

	rec, err := recorder.NewRecorder(ps, "data/positions.csv", log)

	if err != nil {
		log.Error("pupupupuuu", slog.Any("error", err))
	}

	go rec.Start(2 * time.Second)

	select {}
}

func setupLogger() (log *slog.Logger) {
	log = slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))
	return
}
