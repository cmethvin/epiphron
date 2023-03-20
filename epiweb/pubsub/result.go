package pubsub

import (
	"bytes"
	"cloud.google.com/go/pubsub"
	"context"
	"encoding/json"
	"github.com/cmethvin/epiweb"
	"log"
)

type resultsResponse struct {
	ID      string                  `json:"id""`
	Results epiweb.SimulationResult `json:"results"`
}

type ResultsFn func(context.Context, string, epiweb.SimulationResult) error

type ResultsConsumer struct {
	client *pubsub.Client
}

func NewResultsConsumer(projectId string) (*ResultsConsumer, error) {
	client, err := pubsub.NewClient(context.Background(), projectId)
	if err != nil {
		return nil, err
	}

	return &ResultsConsumer{
		client: client,
	}, nil
}

func (r *ResultsConsumer) Listen(subscriptionId string, resultsFn ResultsFn) error {
	if err := r.client.Subscription(subscriptionId).Receive(context.Background(), func(ctx context.Context, msg *pubsub.Message) {
		var resp resultsResponse

		if err := json.NewDecoder(bytes.NewBuffer(msg.Data)).Decode(&resp); err != nil {
			log.Printf("Error decoding results message: %v", err)
			msg.Nack()
			return
		}

		log.Printf("Got message %s", msg.Data)

		if err := resultsFn(ctx, resp.ID, resp.Results); err != nil {
			log.Printf("Error saving results: %v", err)
			msg.Nack()
			return
		}

		msg.Ack()
	}); err != nil {
		return err
	}

	return nil
}
