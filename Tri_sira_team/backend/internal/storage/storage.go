package storage

import (
	"sync"
	"time"
)

// BeaconData хранит данные одного маячка
type BeaconData struct {
	RSSI      int
	Distance  float64
	UpdatedAt time.Time
}

// Storage отвечает за хранение последних данных по маякам
type Storage struct {
	mu   sync.RWMutex
	data map[string]BeaconData
}

// NewStorage инициализирует сторедж
func NewStorage() *Storage {
	return &Storage{
		data: make(map[string]BeaconData),
	}
}

// Set обновляет данные по маяку
func (s *Storage) Set(beaconID string, rssi int, distance float64) {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.data[beaconID] = BeaconData{
		RSSI:      rssi,
		Distance:  distance,
		UpdatedAt: time.Now(),
	}
}

// Get возвращает данные по маяку
func (s *Storage) Get(beaconID string) (BeaconData, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	data, ok := s.data[beaconID]
	return data, ok
}

// GetAll возвращает все данные
func (s *Storage) GetAll() map[string]BeaconData {
	s.mu.RLock()
	defer s.mu.RUnlock()

	// копия мапы, чтобы снаружи не меняли оригинал
	result := make(map[string]BeaconData, len(s.data))
	for k, v := range s.data {
		result[k] = v
	}
	return result
}
