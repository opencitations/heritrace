# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

export HOST_UID := $(shell id -u)
export HOST_GID := $(shell id -g)

DEV_COMPOSE := docker compose -f dev/docker-compose.dev.yaml
USER_TEST_DIR := .user-test

.PHONY: frontend frontend-dev dev demo demo-iswc2026 user-test-enduser user-test-technician

frontend:
	cd frontend && dart run slang && flutter build web --release

frontend-dev:
	cd frontend && dart run slang && flutter run -d chrome \
		--web-hostname 127.0.0.1 --web-port 5100 \
		--web-tls-cert-path ../dev/ssl/cert.pem --web-tls-cert-key-path ../dev/ssl/key.pem \
		--dart-define=API_BASE_URL=https://127.0.0.1:5000

dev:
	./dev/fetch-databases.sh
	$(DEV_COMPOSE) up --build

demo:
	./dev/fetch-databases.sh
	$(DEV_COMPOSE) -f dev/docker-compose.demo.yaml up --build

demo-iswc2026:
	docker compose -f demo/iswc2026/docker-compose.yml up

user-test-enduser user-test-technician: user-test-%:
	cd user_testing/packages && ./build-online-packages.sh
	unzip -oq user_testing/packages/heritrace-$*-testing.zip -d $(USER_TEST_DIR)
	cd $(USER_TEST_DIR)/heritrace-$*-testing && ./start.sh
