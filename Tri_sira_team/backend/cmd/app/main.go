package main

import (
	"log/slog"
	"os"
	m "service/internal/mosquitto"
)

func main() {
	// Настройка логгера
	log := setupLogger()

	// Создание клиента для MQTT брокера, по сути это как консьюмер для кафки
	var cfg m.Config
	cfg.Broker = "mosquitto:" + os.Getenv("MOSQUITTO_INTERNAL_PORT")
	cfg.ClientId = "service"
	cfg.Username = os.Getenv("MOSQUITTO_USER")
	cfg.Password = os.Getenv("MOSQUITTO_PASSWORD")
	_, err := m.NewClient(cfg, log)
	if err != nil {
		log.Error("creating broker client error", slog.Any("error: %w", err))
	}
	log.Info("service connected to broker")

}

func setupLogger() (log *slog.Logger) {
	log = slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))
	return
}
