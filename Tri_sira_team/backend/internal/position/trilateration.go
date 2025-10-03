package position

import (
	"fmt"
	"math"

	"gonum.org/v1/gonum/optimize"
)

type Beacon struct {
	X, Y     float64
	Distance float64
}

type Trilateration struct {
	beacons []Beacon
}

func NewTrilateration() *Trilateration {
	return &Trilateration{}
}

func (t *Trilateration) SetBeacons(beacons []Beacon) {
	t.beacons = beacons
}

func (t *Trilateration) EstimatePosition() (float64, float64, error) {
	if len(t.beacons) < 3 {
		return 0, 0, fmt.Errorf("нужно минимум 3 маяка для расчёта")
	}

	initX, initY := 0.0, 0.0

	fn := func(x []float64) float64 {
		estX, estY := x[0], x[1]
		err := 0.0
		for _, b := range t.beacons {
			dx := estX - b.X
			dy := estY - b.Y
			dist := math.Sqrt(dx*dx + dy*dy)
			err += (dist - b.Distance) * (dist - b.Distance)
		}
		return err
	}

	problem := optimize.Problem{
		Func: fn,
	}

	result, err := optimize.Minimize(problem, []float64{initX, initY}, nil, nil)
	if err != nil {
		return 0, 0, err
	}

	return result.X[0], result.X[1], nil
}
