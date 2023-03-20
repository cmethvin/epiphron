package http

import (
	"context"
	"encoding/json"
	"fmt"
	"github.com/cmethvin/epiweb"
	"github.com/gorilla/mux"
	"html/template"
	"log"
	"net/http"
	"strconv"
	"time"
)

type Server struct {
	SimulationService *epiweb.SimulationService
	template          *template.Template
}

func (s *Server) Start() {
	var err error
	if s.template, err = template.ParseGlob("tmpl/*.tmpl"); err != nil {
		log.Fatal(err)
	}

	router := mux.NewRouter()
	router.PathPrefix("/static/").Handler(http.StripPrefix("/static/", http.FileServer(http.Dir("/static"))))
	router.HandleFunc("/", s.handleIndex()).Methods("GET")
	router.HandleFunc("/sim", s.handleInitiateSim()).Methods("POST")
	router.HandleFunc("/sim/{id}", s.handleGetSim()).Methods("GET")

	api := router.PathPrefix("/api").Subrouter()
	{
		api.HandleFunc("/results/{id}", s.handleGetResults()).Methods("GET")
	}

	server := &http.Server{
		Addr:         ":8080",
		Handler:      router,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
	}

	log.Println("Listening on port 8080")
	log.Fatal(server.ListenAndServe())
}

func (s *Server) handleIndex() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Add("Content-Type", "text/html")
		if err := s.template.ExecuteTemplate(w, "index", nil); err != nil {
			log.Println(err)
			http.Error(w, "unknown error", http.StatusInternalServerError)
		}
	}
}

func (s *Server) handleInitiateSim() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var (
			err          error
			retirePeriod int
			workYears    int
			id           string
		)

		if retirePeriod, err = strconv.Atoi(r.PostFormValue("retire-period")); err != nil {
			log.Println(err)
			http.Error(w, "invalid retire period", http.StatusBadRequest)
			return
		}

		log.Println(fmt.Sprintf("Retire period: %v", retirePeriod))

		ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
		defer cancel()

		if id, err = s.SimulationService.Create(ctx, retirePeriod, workYears); err != nil {
			log.Println(err)
			http.Error(w, "unknown error", http.StatusInternalServerError)
			return
		}

		http.Redirect(w, r, "/sim/"+id, http.StatusFound)
	}
}

func (s *Server) handleGetSim() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		id := mux.Vars(r)["id"]

		ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
		defer cancel()

		sim, err := s.SimulationService.Get(ctx, id)
		if err != nil {
			log.Println(err)
			http.Error(w, "unknown error", http.StatusInternalServerError)
			return
		}

		if err := s.template.ExecuteTemplate(w, "sim", sim); err != nil {
			log.Println(err)
			http.Error(w, "unknown error", http.StatusInternalServerError)
		}
	}
}

func (s *Server) handleGetResults() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		id := mux.Vars(r)["id"]

		ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
		defer cancel()

		sim, err := s.SimulationService.Get(ctx, id)
		if err != nil {
			log.Println(err)
			http.Error(w, "unknown error", http.StatusInternalServerError)
			return
		}

		w.Header().Add("Content-Type", "application/json")
		if err := json.NewEncoder(w).Encode(&sim); err != nil {
			log.Println("error encoding json")
		}
	}
}
