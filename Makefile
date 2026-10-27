.PHONY: install up down generate load dbt test report all superset
export PGHOST ?= localhost
export PGPORT ?= 5432
export PGUSER ?= mp
export PGPASSWORD ?= mp
export PGDATABASE ?= marketplace

install:
	pip install -r requirements.txt
up:
	docker compose up -d --wait postgres
down:
	docker compose down
generate:
	python -m src.generator.generate --out data
load:
	python -m src.loader.load --data data
dbt:
	cd dbt && dbt build --profiles-dir .
test:
	python -m pytest -q
report:
	python -m src.report
superset:
	docker compose --profile bi up -d --build
all: generate load dbt test report
