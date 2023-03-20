package main

import (
	"github.com/cmethvin/epiweb"
	"github.com/cmethvin/epiweb/datastore"
	"github.com/cmethvin/epiweb/http"
	"github.com/cmethvin/epiweb/pubsub"
	"log"
)

const (
	// TODO: move these to external config
	projectId    = "epiphron"
	simTopicId   = "simulation_topic"
	resultsSubId = "results_topic-sub"
)

func main() {
	simDao, err := datastore.NewSimulationDao(projectId)
	if err != nil {
		log.Fatal(err)
	}

	jobQueue, err := pubsub.NewJobQueue(projectId, simTopicId)
	if err != nil {
		log.Fatal(err)
	}

	resultsConsumer, err := pubsub.NewResultsConsumer(projectId)
	if err != nil {
		log.Fatal(err)
	}

	simService := &epiweb.SimulationService{
		SimulationDao: simDao,
		JobQueue:      jobQueue,
	}

	server := &http.Server{
		SimulationService: simService,
	}

	go func() {
		if err := resultsConsumer.Listen(resultsSubId, simService.SaveResults); err != nil {
			log.Fatal(err)
		}
	}()

	server.Start()
}
