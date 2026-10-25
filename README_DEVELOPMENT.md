# Remote Career Navigator - Development

## Stack

- Backend: Python + FastAPI
- Frontend: Angular + TypeScript
- Database objetivo: PostgreSQL + pgvector
- Queue objetivo: Redis + Celery

## Docker en Ubuntu

La estructura de despliegue queda homologada al estilo de Tecolyt:

```bash
cp .env.example .env
docker compose --env-file .env up --build
```

La aplicacion queda disponible en:

```text
http://localhost:8050
```

Para correr detras de Kong con prefijo, define:

```bash
UI_PREFIX=/rcn/ui
RCN_UI_PREFIX=/rcn/ui
```

En servidor Ubuntu, el flujo recomendado es:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
cp .env.example .env
nano .env
docker compose --env-file .env up -d --build
```

Para ver estado y logs:

```bash
docker compose --env-file .env ps
docker compose --env-file .env logs -f app
```

Para actualizar despues de subir cambios:

```bash
docker compose --env-file .env up -d --build
```

## Backend

Las credenciales de la base de datos van en:

```text
backend/.env
```

Usa [backend/.env.example](backend/.env.example) como plantilla. La variable principal es:

```bash
RCN_DATABASE_URL="postgresql+psycopg://usuario:password@localhost:5432/rcn"
```

Prerequisito en Debian/Ubuntu si `python3 -m venv` falla:

```bash
sudo apt install python3.14-venv
```

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://localhost:8000/api/health
```

Crear un perfil conectado a la base:

```bash
curl -X POST http://localhost:8000/api/candidate-profiles \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Marc Demo","headline":"Senior Software Engineer","country":"Peru","years_experience":10,"english_level":"Intermediate"}'
```

Listar perfiles:

```bash
curl http://localhost:8000/api/candidate-profiles
```

## Frontend

```bash
cd frontend
npm install
npm start
```

Angular queda disponible en:

```text
http://localhost:4200
```

## Agente local con Firefox

El agente se instala en el equipo que tiene Firefox, por separado del servicio Docker.
No necesita PostgreSQL ni arrancar FastAPI.

```bash
cd backend
uv venv .venv
uv pip install --python .venv/bin/python -e '.[browser,dev]'
.venv/bin/rcn-agent doctor
```

También se puede usar `python3 -m venv .venv` y `.venv/bin/pip install -e '.[browser,dev]'`
si `python3-venv` está instalado.

La guía de comandos y el alcance de esta entrega están en
[LOCAL_CAREER_AGENT.md](docs/LOCAL_CAREER_AGENT.md).

Verificación del backend y del agente:

```bash
cd backend
.venv/bin/ruff check app tests
.venv/bin/python -m pytest -q
```

Las pruebas de navegador crean **otro Firefox con un perfil temporal** y un puerto
Marionette distinto. No usan tu cuenta ni hacen solicitudes a LinkedIn:

```bash
RCN_FIREFOX_TESTS=1 .venv/bin/python -m pytest -q tests/test_firefox_agent.py
```

Estas pruebas requieren Firefox y geckodriver en PATH. En Ubuntu con Snap usan un
perfil temporal en `~/snap/firefox/common/` para que Firefox pueda leerlo.
