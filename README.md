# 🪓 PubSub Knife

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
- Publicar mensagens (sync, async, callback, custom batch)
- Consumir mensagens (modo pull e streaming)
- Ferramentas úteis para testes de observabilidade (latência, throughput etc.)

---

## 🛠️ Instalação

```bash
# Clonar o repositório
git clone https://github.com/seu-usuario/pubsub-knife.git
cd pubsub-knife

# Criar e ativar o ambiente virtual
python -m venv .venv
source .venv/bin/activate

# Instalar dependências
poetry install
```

---

## 🧪 Execução

### 1. Subir o Pub/Sub Emulator com Docker

```bash
docker compose up -d
```

> Certifique-se de exportar as variáveis de ambiente:

```bash
export PUBSUB_PROJECT_ID=dummy-project
export PUBSUB_EMULATOR_HOST=localhost:8085
```

### 2. Usar o CLI

```bash
# Listar tópicos
poetry run pubsub-knife topic list-topics

# Criar tópico
poetry run pubsub-knife topic create --name=meu-topico

# Publicar mensagem
poetry run pubsub-knife publisher sync --topic=meu-topico --message="Hello, PubSub!"
```

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
