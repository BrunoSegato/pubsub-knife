.PHONY: test-unit test-ci-html test-ci test-integration check lint format mypy help hooks pre-commit pre-commit-refresh topic-delete topic-get topic-help topic-list subscription-get subscription-help subscription-list subscription-delete subscription-create publisher-callback publisher-sync consumer-pull-with-ack consumer-pull-without-ack publisher-help consumer-help
.DEFAULT_GOAL := help

topic-help:
	@poetry run pubsub-knife topic --help

topic-list:
	@poetry run pubsub-knife topic list-topics

topic-get:
	@test -n "$(name)" || (echo "Uso: make topic-get name='nome_do_topico'" && exit 1)
	@poetry run pubsub-knife topic get --name="$(name)"

topic-delete:
	@test -n "$(name)" || (echo "Uso: make topic-delete name='nome_do_topico'" && exit 1)
	@poetry run pubsub-knife topic delete --name="$(name)"

topic-create:
	@test -n "$(name)" || (echo "Uso: make topic-create name='nome_do_topico'" && exit 1)
	@poetry run pubsub-knife topic create --name="$(name)"

subscription-help:
	@poetry run pubsub-knife subscription --help

subscription-list:
	@poetry run pubsub-knife subscription list-subscriptions

subscription-get:
	@test -n "$(name)" || (echo "Uso: make subscription-get name='nome_da_assinatura'" && exit 1)
	@poetry run pubsub-knife subscription get --name="$(name)"

subscription-delete:
	@test -n "$(name)" || (echo "Uso: make subscription-delete name='nome_da_assinatura'" && exit 1)
	@poetry run pubsub-knife subscription delete --name="$(name)"

subscription-create:
	@test -n "$(name)" || (echo "Uso: make subscription-create name='nome_da_assinatura'" && exit 1)
	@test -n "$(topic-name)" || (echo "Uso: make subscription-create topic-name='nome_do_topico'" && exit 1)
	@poetry run pubsub-knife subscription create --name="$(name)" --topic-name="$(topic-name)"

publisher-help:
	@poetry run pubsub-knife publisher --help

publisher-sync:
	@test -n "$(topic)" || (echo "Uso: make publisher-sync topic='nome_do_topico'" && exit 1)
	@poetry run pubsub-knife publisher sync --topic="$(topic)" $(if $(message),--message=$(message)) $(if $(json),--json='$(json)') $(if $(repeat),--repeat=$(repeat)) $(if $(gzip),--gzip) $(if $(interval),--interval=$(interval))

publisher-callback:
	@test -n "$(topic)" || (echo "Uso: make publisher-sync topic='nome_do_topico'" && exit 1)
	@poetry run pubsub-knife publisher with-callback --topic="$(topic)" $(if $(message),--message=$(message)) $(if $(json),--json='$(json)') $(if $(repeat),--repeat=$(repeat)) $(if $(gzip),--gzip) $(if $(interval),--interval=$(interval))

consumer-help:
	@poetry run pubsub-knife consumer --help

consumer-pull-with-ack:
	@test -n "$(subscription)" || (echo "Uso: make consumer-pull-with-ack subscription='nome_da_assinatura'" && exit 1)
	@test -n "$(max-messages)" || (echo "Uso: make consumer-pull-with-ack max-messages='10'" && exit 1)
	@poetry run pubsub-knife consumer pull --subscription="$(subscription)" --max-messages="$(max-messages)" --auto-ack

consumer-pull-without-ack:
	@test -n "$(subscription)" || (echo "Uso: make consumer-pull-with-ack subscription='nome_da_assinatura'" && exit 1)
	@test -n "$(max-messages)" || (echo "Uso: make consumer-pull-with-ack max_messages='10'" && exit 1)
	@poetry run pubsub-knife consumer pull --subscription="$(subscription)" --max-messages="$(max-messages)"

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
	@echo "📘 PubSub Knife CLI - Comandos disponíveis via Makefile"
	@echo ""
	@echo "🔹 TÓPICOS"
	@echo "  make topic-help                            # Mostra ajuda dos comandos de tópico"
	@echo "  make topic-list                            # Lista todos os tópicos"
	@echo "  make topic-get name=TOPICO                 # Mostra detalhes de um tópico"
	@echo "  make topic-create name=TOPICO              # Cria um novo tópico"
	@echo "  make topic-delete name=TOPICO              # Remove um tópico existente"
	@echo ""
	@echo "🔹 ASSINATURAS"
	@echo "  make subscription-help                     # Mostra ajuda dos comandos de assinatura"
	@echo "  make subscription-list                     # Lista todas as assinaturas"
	@echo "  make subscription-get name=ASSINATURA      # Mostra detalhes de uma assinatura"
	@echo "  make subscription-create name=ASSINATURA topic-name=TOPICO    # Cria assinatura para um tópico"
	@echo "  make subscription-delete name=ASSINATURA   # Remove uma assinatura existente"
	@echo ""
	@echo "🔹 PUBLICADOR"
	@echo "  make publisher-help                        # Mostra ajuda dos comandos de publisher"
	@echo "  make publisher-sync topic=TOPICO message=MENSAGEM            # Publica mensagem de forma síncrona"
	@echo "  make publisher-callback topic=TOPICO message=MENSAGEM        # Publica com add_done_callback"
	@echo ""
	@echo "🔹 CONSUMIDOR"
	@echo "  make consumer-help                         # Mostra ajuda dos comandos de consumer"
	@echo "  make consumer-pull-with-ack subscription=ASSINATURA max-messages=N    # Consome e acka as mensagens"
	@echo "  make consumer-pull-without-ack subscription=ASSINATURA max-messages=N # Consome sem ackar"
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
	@echo "ℹ️  Exemplo: make topic-create name=meu-topico"
