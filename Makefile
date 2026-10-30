.PHONY: install emulator-up emulator-down test-unit test-ci-html test-ci test-integration test-matching check lint format mypy help hooks pre-commit pre-commit-refresh
.DEFAULT_GOAL := help

install:
	pipx install --force .

emulator-up:
	docker compose up -d

emulator-down:
	docker compose down

hooks:
	poetry run pre-commit install

pre-commit-refresh:
	poetry run pre-commit clean
	poetry run pre-commit install

pre-commit:
	poetry run pre-commit run --all --verbose

lint:
	poetry run ruff check .

format:
	poetry run ruff check . --fix

mypy:
	poetry run mypy src/

check: lint mypy

test-integration:
	poetry run pytest -s -m "integration"

test-ci:
	poetry run pytest --cov=src --cov-report=xml

test-ci-html:
	poetry run pytest -v tests --cov=src --cov-report=html

test-unit:
	poetry run pytest -s -m "unit"

test-matching:
	poetry run pytest -s -rx -k $(Q) --pdb tests

help:
	@echo ""
	@echo "📘 PubSub Knife - Comandos de desenvolvimento"
	@echo ""
	@echo "🔹 SETUP"
	@echo "  make install                               # Instala o CLI globalmente via pipx (comandos pk / pubsub-knife)"
	@echo "  make emulator-up                           # Sobe o Pub/Sub Emulator (docker compose)"
	@echo "  make emulator-down                         # Derruba o Pub/Sub Emulator"
	@echo ""
	@echo "🔹 TESTES"
	@echo "  make test-unit                             # Executa apenas testes unitários (-m 'unit')"
	@echo "  make test-integration                      # Executa apenas testes de integração (-m 'integration')"
	@echo "  make test-ci                               # Executa testes + cobertura (report em XML)"
	@echo "  make test-ci-html                          # Executa testes + cobertura em HTML"
	@echo ""
	@echo "🔹 QUALIDADE DE CÓDIGO"
	@echo "  make check                                 # Executa lint + mypy"
	@echo "  make lint                                  # Executa ruff (análise estática)"
	@echo "  make format                                # Executa ruff com autofix"
	@echo "  make mypy                                  # Executa verificação de tipos com mypy"
	@echo ""
	@echo "🔹 GIT HOOKS"
	@echo "  make hooks                                 # Instala hooks com pre-commit"
	@echo "  make pre-commit                            # Executa todos os hooks"
	@echo "  make pre-commit-refresh                    # Limpa e reinstala os hooks"
	@echo ""
	@echo "ℹ️  Para usar o CLI: pk --help"
