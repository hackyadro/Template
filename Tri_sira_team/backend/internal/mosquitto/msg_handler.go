package mosquitto

import "log/slog"

type MqqtMsgHandler struct {
	// todo: придумать чё со стореджем то делать (прометеус?????)
	log *slog.Logger
}

func NewHandler(log *slog.Logger) *MqqtMsgHandler {
	return &MqqtMsgHandler{log: log}
}

func (h *MqqtMsgHandler) HandleMsg(msg []byte) error {

	return nil
}
