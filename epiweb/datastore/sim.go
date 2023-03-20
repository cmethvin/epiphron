package datastore

import (
	"cloud.google.com/go/datastore"
	"context"
	"github.com/cmethvin/epiweb"
)

const typeName = "Simulation"

type SimulationDao struct {
	client *datastore.Client
}

func NewSimulationDao(projectId string) (*SimulationDao, error) {
	ctx := context.Background()

	if client, err := datastore.NewClient(ctx, projectId); err != nil {
		return nil, err
	} else {
		return &SimulationDao{client}, nil
	}
}

func (s *SimulationDao) Save(ctx context.Context, sim epiweb.Simulation) error {
	key := datastore.NameKey(typeName, sim.ID, nil)

	if _, err := s.client.Put(ctx, key, &sim); err != nil {
		return err
	}

	return nil
}

func (s *SimulationDao) Get(ctx context.Context, id string) (sim epiweb.Simulation, err error) {
	key := datastore.NameKey(typeName, id, nil)

	if err = s.client.Get(ctx, key, &sim); err != nil {
		return
	}

	return
}
