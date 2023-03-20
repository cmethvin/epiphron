package epiweb

import (
	"context"
	"errors"
	"time"

	"github.com/google/uuid"
)

type SimulationState int

const (
	Created SimulationState = iota
	Running
	Completed
	Failed
)

func (s SimulationState) String() string {
	switch s {
	case Created:
		return "Created"
	case Running:
		return "Running"
	case Completed:
		return "Completed"
	case Failed:
		return "Failed"
	default:
		return "Invalid"
	}
}

type Simulation struct {
	ID         string           `json:"id"`
	CreateTime time.Time        `json:"createTime"`
	DoneTime   time.Time        `json:"doneTime"`
	Done       bool             `json:"done"`
	State      SimulationState  `json:"state"`
	Results    SimulationResult `json:"results"`
}

type SimulationResult struct {
	SuccessYears            []float64 `json:"Success Years"`
	FinalSavings            []float64 `json:"Final Savings"`
	MeanLowInterest         []float64 `json:"Mean Low Int"`
	MeanMidInterest         []float64 `json:"Mean Mid Int"`
	MeanHighInterest        []float64 `json:"Mean High Int"`
	MeanLowInterestFail     []float64 `json:"Mean Low Int Fail - Annual"`
	MeanMidInterestFail     []float64 `json:"Mean Mid Int Fail - Annual"`
	MeanHighInterestFail    []float64 `json:"Mean High Int Fail - Annual"`
	MeanLowInterestSuccess  []float64 `json:"Mean Low Int Success - Annual"`
	MeanMidInterestSuccess  []float64 `json:"Mean Mid Int Success - Annual"`
	MeanHighInterestSuccess []float64 `json:"Mean High Int Success - Annual"`
	Years                   []float64 `json:"Years"`
	Percentiles             []float64 `json:"Percentiles"`
}

type SimulationService struct {
	SimulationDao SimulationDao
	JobQueue      JobQueue
}

type SimulationDao interface {
	Save(ctx context.Context, sim Simulation) error
	Get(ctx context.Context, id string) (Simulation, error)
}

// Create initializes a simulation, pushes the simulation to the job queue for processing,
// and returns the job ID
func (s *SimulationService) Create(ctx context.Context, retirePeriod, workYears int) (string, error) {
	if retirePeriod <= 0 {
		return "", errors.New("retirement period must be greater than 0")
	}
	if workYears < 0 {
		return "", errors.New("work years must be greater than or equal to 0")
	}

	sim := Simulation{
		ID:         uuid.NewString(),
		CreateTime: time.Now(),
	}

	if err := s.SimulationDao.Save(ctx, sim); err != nil {
		return "", err
	}

	if err := s.JobQueue.Publish(ctx, Job{
		ID:           sim.ID,
		RetirePeriod: retirePeriod,
	}); err != nil {
		return "", err
	}

	return sim.ID, nil
}

func (s *SimulationService) Get(ctx context.Context, id string) (Simulation, error) {
	return s.SimulationDao.Get(ctx, id)
}

func (s *SimulationService) SaveResults(ctx context.Context, id string, results SimulationResult) error {
	sim, err := s.SimulationDao.Get(ctx, id)
	if err != nil {
		return err
	}

	sim.State = Completed
	sim.Done = true
	sim.DoneTime = time.Now()
	sim.Results = results

	if err := s.SimulationDao.Save(ctx, sim); err != nil {
		return err
	}

	return nil
}
