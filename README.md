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

- Criar tópicos e assinaturas a partir de um arquivo YAML (`pk apply`), de forma idempotente
- Criar, listar, obter e remover tópicos
- Criar, listar, obter e remover assinaturas
- Publicar mensagens (texto, arquivo ou stdin; com atributos, ordering key, gzip, repetição e intervalo)
- Publicar várias mensagens de uma vez (uma por linha) e reproduzir capturas do `pk tail --jsonl`
- Consumir mensagens (pull, com descompressão automática de gzip)
- Acompanhar mensagens em tempo real (`pk tail`) de uma assinatura ou de um tópico inteiro
- Navegar pelos tópicos e assinaturas numa interface no terminal (`pk ui`)
- Saída em JSON (`-o json`) em todos os comandos, para usar com `jq` e scripts
- Sempre aponta para o emulador: nunca fala com o GCP real por engano
- Falha rápido (com exit code 1) se o emulador não estiver acessível

---

## 🛠️ Instalação

```bash
git clone https://github.com/BrunoSegato/pubsub-knife.git
cd pubsub-knife

# Instala o CLI globalmente (comandos `pk` e `pubsub-knife`)
make install-cli               # ou: pipx install --force .
```

Para desenvolvimento (venv do projeto com testes, lint e mypy, nas versões do `poetry.lock`):

```bash
make install                   # ou: poetry install
```

> O `pipx` resolve as dependências pelo `pyproject.toml`, não pelo `poetry.lock`.
> Para rodar testes e lint com as mesmas versões do CI, use `make install`.

---

## 🧪 Execução

### 1. Subir o Pub/Sub Emulator com Docker

```bash
docker compose up -d
```

Por padrão o CLI usa `localhost:8085` e o projeto `dummy-project`. Para mudar, use
variáveis de ambiente (`PUBSUB_EMULATOR_HOST`, `PUBSUB_PROJECT_ID`), um arquivo
`.env` ou as opções globais `--emulator-host` e `--project`.

### 2. Declarar tópicos e assinaturas

O emulador perde tudo quando reinicia. Em vez de recriar os recursos na mão,
declare-os em um `pubsub.yaml` (veja o exemplo completo em
[`pubsub.example.yaml`](pubsub.example.yaml)):

```yaml
topics:
  orders:
    subscriptions:
      - orders-worker
      - name: orders-webhook
        push_endpoint: http://host.docker.internal:8000/webhook
        dead_letter_topic: orders-dlq
  orders-dlq:
```

```bash
pk apply                       # lê ./pubsub.yaml; cria o que falta, mantém o que já existe
pk apply infra/pubsub.yaml     # outro arquivo
pk apply --recreate            # remove e recria os recursos do arquivo (para aplicar mudanças)
```

> Assinaturas push: como o emulador roda no Docker, use `host.docker.internal`
> para alcançar uma aplicação rodando na sua máquina.

### 3. Usar o CLI

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
pk pub pedidos '{"id": 1}' -a type=created -a source=test   # atributos
pk pub pedidos '{"id": 1}' --ordering-key cliente-42       # ordering key
pk pub pedidos @eventos.txt --lines        # cada linha vira uma mensagem

# Consumir
pk pull pedidos-worker                     # até 10 mensagens, sem ack
pk pull pedidos-worker -n 50 --ack

# Acompanhar em tempo real (Ctrl+C para sair)
pk tail pedidos-worker                     # só observa: as mensagens voltam para a assinatura ao sair
pk tail pedidos-worker --ack               # consome as mensagens
pk tail -t pedidos                         # tópico inteiro, via assinatura temporária (removida ao sair)
pk tail -t pedidos --jsonl | jq .data      # uma mensagem JSON por linha
pk tail pedidos-worker -n 5 --timeout 30   # para após 5 mensagens ou 30s

# Gravar e reproduzir mensagens (mantém atributos, ordering key e gzip)
pk tail -t pedidos --jsonl > captura.jsonl
pk pub pedidos-v2 @captura.jsonl --envelope
# formato de cada linha: {"data": "...", "attributes": {...}, "ordering_key": "..."}

# Outro projeto/emulador
pk --project outro-projeto --emulator-host localhost:8086 topic list
```

Todos os comandos retornam exit code `1` em caso de erro, então podem ser usados em scripts.

### 4. Saída em JSON

Todos os comandos aceitam `-o json` (ou `--output json`). O JSON vai para o
stdout e as mensagens de erro continuam no stderr, então dá para encadear com `jq`:

```bash
pk topic list -o json | jq -r '.[].name'
pk sub get pedidos-worker -o json | jq .dead_letter_topic
pk pub pedidos '{"id": 1}' -o json | jq -r '.message_ids[0]'
pk pull pedidos-worker -o json | jq '.[] | .data | fromjson'
pk apply -o json | jq '.resources[] | select(.status == "failed")'

export PK_OUTPUT=json                      # vale para todos os comandos da sessão
```

Listas vazias saem como `[]`. No `pk tail`, `-o json` é o mesmo que `--jsonl`:
uma mensagem por linha.

### 5. Interface no terminal

```bash
pk ui
pk --project outro-projeto ui
```

Mostra os tópicos do projeto com as assinaturas de cada um e os detalhes do item
selecionado (push, filtro, dead-letter, ordering, retenção...).

| Tecla | Ação |
|-------|------|
| `p`   | Espia até 10 mensagens da assinatura selecionada, sem consumir |
| `r`   | Recarrega os tópicos e assinaturas |
| `q`   | Sai |

> Espiar devolve as mensagens na hora, mas cada espiada conta como uma tentativa
> de entrega para a dead-letter. Em assinaturas push o `p` fica desativado, porque
> o emulador está entregando as mensagens ao endpoint: use `pk tail -t <tópico>`.

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
- `tests/conftest.py`: fixtures globais (cada teste de integração roda em um projeto próprio no emulador)
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
