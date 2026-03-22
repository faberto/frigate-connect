.PHONY: build run stop logs

IMAGE_NAME := frigateconnect
CONTAINER_NAME := frigateconnect

build:
	podman build --build-arg BUILD_FROM=python:3.12-alpine -t $(IMAGE_NAME) .

run: build
	podman run --rm -d \
		--name $(CONTAINER_NAME) \
		--network host \
		-v ./exports:/media/frigateconnect \
		$(IMAGE_NAME) uv run python3 /app/main.py

stop:
	podman stop $(CONTAINER_NAME)

logs:
	podman logs -f $(CONTAINER_NAME)
