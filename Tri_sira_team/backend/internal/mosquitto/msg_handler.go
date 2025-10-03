package mosquitto

import (
	"encoding/json"
	"log/slog"
	"math"
	s "service/internal/storage"
)

type BeaconMsg struct {
	TxPower    int     `json:"tx_power"`
	BeaconName string  `json:"beacon_name"`
	AvgRssi    float64 `json:"avg_rssi"`
}

type MqqtMsgHandler struct {
	storage *s.Storage
	log     *slog.Logger
}

func NewHandler(storage *s.Storage, log *slog.Logger) *MqqtMsgHandler {
	return &MqqtMsgHandler{storage: storage, log: log}
}

func (h *MqqtMsgHandler) HandleMsg(msg []byte) error {
	var beaconMsg BeaconMsg
	if err := json.Unmarshal(msg, &beaconMsg); err != nil {
		h.log.Error("failed to parse MQTT message", "err", err)
		return err
	}

	n := 2.4
	txPower := -43.40
	distance := math.Pow(10, (float64(txPower)-beaconMsg.AvgRssi)/(10*n))

	h.storage.Set(beaconMsg.BeaconName, int(beaconMsg.AvgRssi), distance)
	h.log.Info("stored beacon data",
		"beacon", beaconMsg.BeaconName,
		"rssi", beaconMsg.AvgRssi,
		"distance", distance,
	)

	return nil
}
