package mosquitto

import (
	"fmt"
	mqtt "github.com/eclipse/paho.mqtt.golang"
	"log/slog"
	s "service/internal/storage"
	"time"
)

type Handler interface {
	HandleMsg(msg []byte) error
}

type Client struct {
	client   mqtt.Client
	handler  Handler
	log      *slog.Logger
	isStoped bool
}

type Config struct {
	Broker   string
	ClientId string
	Username string
	Password string
	Topics   []string
}

const (
	broker_connection_limit = 60 // Максимальное время в секундах, которое сервис будет ожидать пока брокер поднимается
	broker_subscribe_limit  = 30 // Максимальное время в секундах, которое сервис будет ожидать пока брокер подпишется на топик
)

func NewClient(cfg Config, handler Handler, storage *s.Storage, log *slog.Logger) (*Client, error) {
	opts := mqtt.NewClientOptions()
	opts.AddBroker(cfg.Broker)
	opts.SetClientID(cfg.ClientId)
	opts.SetUsername(cfg.Username)
	opts.SetPassword(cfg.Password)

	client := mqtt.NewClient(opts)

	token := client.Connect()
	isConnected := token.WaitTimeout(broker_connection_limit * time.Second)
	if !isConnected {
		return nil, fmt.Errorf("broker connection failed :(")
	}

	for _, topic := range cfg.Topics {
		log.Info("topic", slog.Any("topic", topic))
		token := client.Subscribe(topic, 0, func(_ mqtt.Client, msg mqtt.Message) {
			if err := handler.HandleMsg(msg.Payload()); err != nil {
				log.Error("failed to handle message", "err", err)
			}
		})
		isSubscribed := token.WaitTimeout(broker_subscribe_limit * time.Second)
		if !isSubscribed {
			return nil, fmt.Errorf("topic subscribe failed :(")
		}
	}
	log.Info("EVERYTHING IS OKEY")
	return &Client{client: client, log: log, isStoped: false}, nil
}

func (c *Client) Start(topic string) {
	c.log.Info("starting broker consumer", "topic", topic)

	for {
		if c.isStoped {
			return
		}
		time.Sleep(500 * time.Millisecond)
	}
}

func (c *Client) Stop() {
	c.isStoped = true
	c.client.Disconnect(250)
}
