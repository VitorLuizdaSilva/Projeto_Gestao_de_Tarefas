# NexTask

Aplicação Django com interface HTML/CSS/JavaScript e operações de negócio realizadas pela API Django REST Framework.

## Arquitetura

- Templates Django: somente entregam as páginas (`/`, `/cadastro/`, `/home/`).
- Front-end: JavaScript consome os endpoints em `/api/`.
- API: autenticação JWT, tarefas, equipes, membros, permissões e histórico.
- Persistência: models e migrações existentes preservados.
- Django Admin: continua disponível em `/admin/` e usa autenticação própria do Admin.

## Preparação no Windows / PowerShell

Na pasta que contém `manage.py`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Acesse `http://127.0.0.1:8000/` e crie uma conta. O cadastro público cria usuários com papel `FUNCIONARIO`.

Para acessar o Admin:

```powershell
python manage.py createsuperuser
```

## PostgreSQL

O projeto usa SQLite por padrão. Para PostgreSQL, configure as variáveis no ambiente antes de iniciar o Django:

```powershell
$env:DB_ENGINE="postgres"
$env:DB_NAME="nextask"
$env:DB_USER="postgres"
$env:DB_PASSWORD="SUA_SENHA"
$env:DB_HOST="localhost"
$env:DB_PORT="5432"
```

O Django não carrega automaticamente `.env.example`. Use-o como referência para configurar as variáveis no ambiente ou no serviço de hospedagem. Depois execute:

```powershell
python manage.py migrate
```

`migrate` cria a estrutura no banco selecionado; não copia os registros do SQLite para PostgreSQL. Faça backup e exportação/importação próprios antes de trocar de banco.

## Endpoints principais

- `POST /api/auth/cadastro/`
- `POST /api/auth/login/`
- `POST /api/auth/refresh/`
- `POST /api/auth/logout/`
- `GET /api/auth/me/`
- `GET /api/tarefas/` e operações de detalhe
- `GET /api/tarefas/{id}/historico/`
- `GET /api/equipes/` e operações de detalhe
- `GET|POST /api/equipes/{id}/membros/`
- `PATCH|DELETE /api/equipes/{id}/membros/{membro_id}/`
- `GET /api/usuarios/` (Supremo e Gerente)
- `GET /api/desempenho/` (restrito ao Supremo)

## Observações

- O access token fica em `sessionStorage`; o refresh token é enviado em cookie HttpOnly. `sessionStorage` é acessível ao JavaScript e, portanto, a proteção contra XSS continua importante.
- Em produção, configure `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY` forte, `DJANGO_ALLOWED_HOSTS`, HTTPS, `CSRF_TRUSTED_ORIGINS`, backups e monitoramento.
- O painel calcula indicadores com as tarefas que a API permite ao usuário visualizar. O endpoint global `/api/desempenho/` existente continua restrito ao papel Supremo.
- As permissões reais são sempre validadas no backend; esconder controles na interface não substitui as permissões da API.
