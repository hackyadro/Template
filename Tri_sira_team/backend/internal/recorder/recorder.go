package recorder

import (
	"encoding/csv"
	"fmt"
	"log/slog"
	"os"
	"strconv"
	"time"

	"service/internal/position"
)

type Recorder struct {
	service  *position.PositionService
	file     *os.File
	writer   *csv.Writer
	interval time.Duration
	log      *slog.Logger
}

func NewRecorder(service *position.PositionService, filename string, log *slog.Logger) (*Recorder, error) {
	file, err := os.Create(filename)
	if err != nil {
		return nil, fmt.Errorf("creating file error(")
	}

	writer := csv.NewWriter(file)
	writer.Write([]string{"x", "y"})
	writer.Flush()

	return &Recorder{
		service:  service,
		file:     file,
		writer:   writer,
		interval: 2 * time.Second,
		log:      log,
	}, nil
}

func (r *Recorder) Start(interval time.Duration) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	for range ticker.C {
		x, y, err := r.service.GetCurrentPosition()
		if err != nil {
			r.log.Error("failed to write record", "err", err)
			continue
		}

		record := []string{
			strconv.FormatFloat(x, 'f', 6, 64), // ← заменили
			strconv.FormatFloat(y, 'f', 6, 64), // ← заменили
		}
		if err := r.writer.Write(record); err != nil {
			r.log.Error("failed to write record", "err", err)
		}
		r.writer.Flush()

		r.log.Info("Writing...")
	}
}

func (r *Recorder) Close() error {
	r.writer.Flush()
	return r.file.Close()
}
