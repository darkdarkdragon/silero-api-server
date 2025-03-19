SHELL=/bin/bash

local_setup10:
	python3.10 -m venv env
	env/bin/pip3 install -r requirements.txt

local_setup11:
	python3.11 -m venv env
	env/bin/pip3 install -r requirements.txt

run11:
	env/bin/python3 -m silero_api_server

local_setup:
	python3 -m venv env
	env/bin/pip3 install -r requirements.txt

run:
	env/bin/python3 -m silero_api_server

docker_run:
	docker run --name silero  --rm -p 8001:8001 silero_api_server

docker_build:
	#docker buildx build -t silero_api_server .
	docker build -t silero_api_server --progress plain .

.PHONY: run local_setup local_setup10 local_setup11 run11 docker_build docker_run
