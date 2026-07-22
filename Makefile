GO ?= go

.PHONY: build test serve projects

# Сборка исполняемого файла в bin/
build:
	$(GO) build -o bin/scg-host ./cmd/scg-host

# Тесты хоста
test:
	$(GO) test ./...

# Запуск Web UI на http://localhost:8080
serve: build
	./bin/scg-host serve --addr :8080 --open

# Список подключённых проектов
projects: build
	./bin/scg-host projects
