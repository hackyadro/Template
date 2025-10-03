package position

import (
	"fmt"
	"service/internal/storage"
)

type PositionService struct {
	storage      *storage.Storage
	trilaterator *Trilateration
	beaconCoords map[string][2]float64
}

func NewPositionService(s *storage.Storage, beaconCoords map[string][2]float64) *PositionService {
	return &PositionService{
		storage:      s,
		trilaterator: NewTrilateration(),
		beaconCoords: beaconCoords,
	}
}

func (ps *PositionService) GetCurrentPosition() (float64, float64, error) {
	data := ps.storage.GetAll()

	beacons := make([]Beacon, 0, len(data))
	for id, d := range data {
		coords, ok := ps.beaconCoords[id]
		if !ok {
			continue
		}
		beacons = append(beacons, Beacon{
			X:        coords[0],
			Y:        coords[1],
			Distance: d.Distance,
		})
	}

	if len(beacons) < 3 {
		return 0, 0, fmt.Errorf("недостаточно маяков для расчёта (нужно >=3) !!!!!!!!")
	}

	ps.trilaterator.SetBeacons(beacons)
	return ps.trilaterator.EstimatePosition()
}
