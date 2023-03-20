FROM golang as builder

WORKDIR /app

COPY go.mod .
COPY go.sum .

RUN go mod download

COPY . .

RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build ./cmd/epiweb

FROM scratch

COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /app/epiweb /epiweb
COPY --from=builder /app/tmpl /tmpl
COPY --from=builder /app/static /static
CMD ["/epiweb"]

EXPOSE 8080