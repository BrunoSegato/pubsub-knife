# 🪓 PubSub Knife

![Python](https://img.shields.io/badge/python-^3.13-blue)
![Poetry](https://img.shields.io/badge/poetry-2.1.3+-blueviolet)
![CI](https://github.com/BrunoSegato/pubsub-knife/actions/workflows/ci.yml/badge.svg)
![codecov](https://codecov.io/gh/BrunoSegato/pubsub-knife/branch/main/graph/badge.svg)

**PubSub Knife** é uma ferramenta de linha de comando (CLI) criada com [Typer](https://typer.tiangolo.com/) para facilitar o manuseio do **Google Cloud Pub/Sub Emulator**, oferecendo comandos simples e diretos para gerenciar tópicos, assinaturas e mensagens.

---

## 🎯 Objetivo

Este projeto tem como **prioridade** o suporte ao **Pub/Sub Emulator** para desenvolvedores que desejam testar localmente aplicações que consomem ou publicam eventos em tópicos do Google Cloud Pub/Sub.

---

## 🚀 Tecnologias Utilizadas

- [Typer](https://typer.tiangolo.com/) – para construção do CLI
- [Google Cloud Pub/Sub Client](https://pypi.org/project/google-cloud-pubsub/) – para interação com tópicos e assinaturas
- [Pydantic](https://docs.pydantic.dev/latest/) e [Pydantic Settings](https://docs.pydantic.dev/latest/usage/pydantic_settings/) – para centralização das configurações
- [Pytest](https://docs.pytest.org/) – para testes unitários e de integração
- [Poetry](https://python-poetry.org/) – para gerenciamento de dependências

---

## 🧰 Funcionalidades

- Criar, listar, obter e remover tópicos
- Criar, listar, obter e remover assinaturas
- Publicar mensagens (texto, arquivo ou stdin; com gzip, repetição e intervalo)
- Consumir mensagens (pull, com descompressão automática de gzip)
- Sempre aponta para o emulador: nunca fala com o GCP real por engano
- Falha rápido (com exit code 1) se o emulador não estiver acessível

---

## 🛠️ Instalação

```bash
git clone https://github.com/BrunoSegato/pubsub-knife.git
cd pubsub-knife

# Instala o CLI globalmente (comandos `pk` e `pubsub-knife`)
pipx install .
```

Para desenvolvimento:

```bash
poetry install
```

---

## 🧪 Execução

### 1. Subir o Pub/Sub Emulator com Docker

```bash
docker compose up -d
```

Por padrão o CLI usa `localhost:8085` e o projeto `dummy-project`. Para mudar, use
variáveis de ambiente (`PUBSUB_EMULATOR_HOST`, `PUBSUB_PROJECT_ID`), um arquivo
`.env` ou as opções globais `--emulator-host` e `--project`.

### 2. Usar o CLI

```bash
# Tópicos
pk topic create pedidos
pk topic list                # ou: pk topic ls
pk topic get pedidos
pk topic delete pedidos      # ou: pk topic rm pedidos

# Assinaturas (`sub` é um atalho para `subscription`)
pk sub create pedidos-worker --topic pedidos
pk sub list
pk sub get pedidos-worker
pk sub delete pedidos-worker

# Publicar
pk pub pedidos "Hello, PubSub!"
pk pub pedidos '{"id": 1}' --json          # valida o JSON antes de publicar
pk pub pedidos @payload.json               # lê de um arquivo
cat payload.json | pk pub pedidos          # lê do stdin
pk pub pedidos "ping" --repeat 10 --interval 0.5 --gzip

# Consumir
pk pull pedidos-worker                     # até 10 mensagens, sem ack
pk pull pedidos-worker -n 50 --ack

# Outro projeto/emulador
pk --project outro-projeto --emulator-host localhost:8086 topic list
```

Todos os comandos retornam exit code `1` em caso de erro, então podem ser usados em scripts.

---

## 🧪 Testes

O projeto está preparado para testes unitários e de integração utilizando `pytest`.

### Comandos disponíveis

```bash
# Testes unitários
make test-unit

# Testes de integração (com o PubSub Emulator rodando)
make test-integration

# Testes com relatório de cobertura (formato XML)
make test-ci

# Testes com relatório HTML
make test-ci-html
```

### Estrutura de testes

- `tests/integration/pubsub_knife/test_*.py`: testes de integração
- `tests/utils.py`: helpers como criação/remoção de tópicos/assinaturas
- `tests/conftest.py`: fixtures globais (como cleanup automático)
- `tests/unit/test_*.py`: testes unitários

---

## 🧾 Requisitos

- Python >= 3.13
- Docker (para rodar o emulador)
- `poetry` (para gerenciar dependências)

---

## 🧑‍💻 Autor

Desenvolvido por **Bruno Segato**
📧 brunosegatoit@gmail.com

---

## 📄 Licença

Este projeto está sob a licença MIT.
