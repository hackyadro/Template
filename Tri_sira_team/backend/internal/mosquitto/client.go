package mosquitto

import (
	"fmt"
	"log/slog"
	"time"

	mqtt "github.com/eclipse/paho.mqtt.golang"
)

type Client struct {
	client mqtt.Client
	log    *slog.Logger
}

type Config struct {
	Broker   string
	ClientId string
	Username string
	Password string
}

const (
	broker_connection_limit = 60 // Максимальное время в секундах, которое сервис будет ожидать пока брокер поднимается
)

func NewClient(cfg Config, log *slog.Logger) (*Client, error) {
	var opts mqtt.ClientOptions
	opts.AddBroker(cfg.Broker)
	opts.SetClientID(cfg.ClientId)
	opts.SetUsername(cfg.Username)
	opts.SetPassword(cfg.Password)

	client := mqtt.NewClient(&opts)

	token := client.Connect()
	isConnected := token.WaitTimeout(broker_connection_limit * time.Second)
	if !isConnected {
		return nil, fmt.Errorf("broker connection failed :(")
	}

	return &Client{client: client, log: log}, nil
}
