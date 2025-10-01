FROM golang:latest

COPY ./ ./

RUN go build -o service ./cmd/app/main.go

CMD ["./service"]