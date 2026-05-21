# AcertaConta

Sistema web para divisão de despesas em grupo. Permite que usuários criem grupos, registrem gastos compartilhados e visualizem saldos em tempo real — indicando quem deve quanto a quem.

Projeto desenvolvido para a disciplina de Engenharia de Software — Universidade Presbiteriana Mackenzie (FCI).

---

## Funcionalidades

- Cadastro e autenticação de usuários com JWT
- Criação de grupos com link de convite único
- Entrada em grupos via link
- Registro de despesas com divisão automática e igualitária entre participantes
- Cálculo de saldos por grupo (quanto cada membro pagou e deve)
- Interface web servida diretamente pela API
- Suporte a PWA (manifest + service worker)

---

## Tecnologias

| Camada | Tecnologia |
|---|---|
| Backend | Python 3, FastAPI |
| Banco de dados | SQLite com SQLAlchemy ORM |
| Autenticação | JWT (python-jose) + bcrypt (passlib) |
| Validação | Pydantic v2 |
| Frontend | HTML/CSS/JS estático (servido pelo FastAPI) |

---

## Estrutura do Projeto

```
AcertaConta/
├── backend/
│   ├── main.py          # Rotas e lógica da API (FastAPI)
│   └── database.py      # Modelos SQLAlchemy e schemas Pydantic
├── frontend/
│   ├── index.html
│   ├── manifest.json
│   ├── sw.js
│   ├── icon-192.png
│   └── icon-512.png
└── README.md
```

---

## Modelo de Dados

- **Usuario** — armazena nome, e-mail e hash da senha
- **Grupo** — possui um criador, uma lista de participantes (N:N) e um link de convite UUID
- **Despesa** — registrada por um usuário dentro de um grupo, com valor, descrição e data
- **Divisao** — representa a parte de cada participante em uma despesa, com flag de pagamento

---

## API — Endpoints

### Autenticação
| Método | Rota | Descrição |
|---|---|---|
| POST | `/auth/cadastro` | Registra novo usuário e retorna token |
| POST | `/auth/login` | Autentica e retorna token JWT |
| GET | `/auth/me` | Retorna dados do usuário autenticado |

### Grupos
| Método | Rota | Descrição |
|---|---|---|
| POST | `/grupos` | Cria um novo grupo |
| GET | `/grupos` | Lista grupos do usuário autenticado |
| GET | `/grupos/{id}` | Detalhes de um grupo |
| POST | `/grupos/entrar/{link}` | Entra em um grupo pelo link de convite |

### Despesas e Saldos
| Método | Rota | Descrição |
|---|---|---|
| POST | `/despesas` | Registra uma despesa e divide entre participantes |
| GET | `/grupos/{id}/despesas` | Lista despesas de um grupo |
| GET | `/grupos/{id}/saldos` | Retorna saldo líquido de cada participante |

---

## Como Executar

### Pré-requisitos

- Python 3.10 ou superior
- pip

### Instalação

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/acerta-conta.git
cd acerta-conta

# Instale as dependências
pip install fastapi uvicorn sqlalchemy passlib[bcrypt] python-jose[cryptography] pydantic[email]

# Inicie o servidor
uvicorn backend.main:app --reload
```

A aplicação estará disponível em `http://localhost:8000`.

A documentação interativa da API (Swagger UI) pode ser acessada em `http://localhost:8000/docs`.

---

# Autores

Projeto desenvolvido em grupo — Engenharia de Software, 2025.

- Guillermo 
- José
- Felipe
- Rodrigo

---

# Link Video Apresentação: https://youtu.be/GSFA5mtf8cA
## Link Site AcertaConta: https://greeter-ability-kindly.ngrok-free.dev

---



## Observações Técnicas

- O banco de dados SQLite é criado automaticamente na primeira execução (`acertaconta.db`)
- A `SECRET_KEY` do JWT está definida diretamente no código para fins acadêmicos; em produção deve ser configurada via variável de ambiente
- A divisão de despesas é igualitária; valores são arredondados para duas casas decimais
