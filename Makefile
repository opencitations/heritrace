# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

export HOST_UID := $(shell id -u)
export HOST_GID := $(shell id -g)

DEV_COMPOSE := docker compose -f dev/docker-compose.dev.yaml
USER_TEST_DIR := .user-test

.PHONY: dev demo demo-iswc2026 user-test-enduser user-test-technician

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
