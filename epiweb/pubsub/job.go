package pubsub

import (
	"bytes"
	"cloud.google.com/go/pubsub"
	"context"
	"encoding/json"
	"fmt"
	"github.com/cmethvin/epiweb"
	"log"
)

type jobData struct {
	ID           string `json:"id"`
	RetirePeriod int    `json:"retirePeriod"`
}

type JobQueue struct {
	topic  string
	client *pubsub.Client
}

func NewJobQueue(projectId, topic string) (*JobQueue, error) {
	ctx := context.Background()

	client, err := pubsub.NewClient(ctx, projectId)
	if err != nil {
		return nil, fmt.Errorf("pubsub Publish: %v", err)
	}

	return &JobQueue{
		topic:  topic,
		client: client,
	}, nil
}

func (j *JobQueue) Publish(ctx context.Context, job epiweb.Job) error {
	topic := j.client.Topic(j.topic)
	defer topic.Stop()

	result := topic.Publish(ctx, createMessageFromJob(job))

	id, err := result.Get(ctx)
	if err != nil {
		log.Println(err)
		return err
	}

	log.Println("Published job " + id)

	return nil
}

func createMessageFromJob(job epiweb.Job) *pubsub.Message {
	var b bytes.Buffer
	if err := json.NewEncoder(&b).Encode(jobData{
		ID:           job.ID,
		RetirePeriod: job.RetirePeriod,
	}); err != nil {
		log.Println(err)
		return nil
	}

	return &pubsub.Message{
		Data: b.Bytes(),
	}
}
