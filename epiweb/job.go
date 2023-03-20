package epiweb

import "context"

type Job struct {
	ID           string
	RetirePeriod int
	WorkYears    int
}

type JobQueue interface {
	Publish(ctx context.Context, job Job) error
}
