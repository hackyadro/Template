FROM golang:latest

WORKDIR /app

COPY ./ ./

RUN go build -o service ./cmd/app/main.go

CMD ["./service"]