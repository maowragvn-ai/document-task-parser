# 📄 vantage-document-parser

An open-source **Document Parser** application that leverages:

* 🚀 **FastAPI** for the backend API
* 🧠 **llama-index-core**, **Kotaemon**, **Markitdown** for document understanding and parsing
* **Celery** for asynchronous task processing
* 🔧 Fully Dockerized environment with development and production modes

> Built for intelligent document parsing at scale with modular design and API-first architecture.

---

## 📚 Table of Contents

* [⚙️ Installation](#️-installation)
* [🔐 Environment Setup](#-environment-setup)
* [🚀 Running the Application](#-running-the-application)
* [🐳 Run All Services with Docker](#-run-all-service-with-docker)
* [🛠 Makefile Commands](#-make-file-cmd)
* [🤝 Contributing](#-contributing)
* [📄 License](#-license)

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/maowragvn-ai/document-task-parser.git
cd document-task-parser
```

### 2. (Optional) Create a virtual environment

* **Unix/macOS:**

  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

* **Windows:**

  ```bash
  python -m venv venv
  .\venv\Scripts\activate
  ```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🔐 Environment Setup

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Update `.env` with your API keys and database credentials:

```env
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=
TAVILY_API_KEY=

## Local dev DB
DB_USER=myuser
DB_PASSWORD=1
DB_HOST=postgres
DB_PORT=5432
DB_NAME=dvp_database

## Redis broker URL
CELERY_BROKER_URL=redis://redis:6379/0
```

---

## 🚀 Running the Application

### 1. Start Celery Worker

```bash
celery -A src.celery_worker worker --loglevel=info
```

### 2. Ensure PostgreSQL and Redis are running

* PostgreSQL: [localhost:5432](http://localhost:5432)
* Redis: [localhost:6379](http://localhost:6379)

> 💡 Use `init_db.sh` to initialize the database if needed.

```bash
./init_db.sh
```

### 3. Start the FastAPI backend

```bash
uvicorn app_fastapi:app --host 0.0.0.0 --port 8000 --reload
```

* API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. (Optional) Start Streamlit frontend *(currently not supported)*

```bash
streamlit run app_streamlit.py --server.port=8501 --server.address=0.0.0.0
```

* UI: [http://localhost:8501](http://localhost:8501)

### 5. Run DB migrations

```bash
alembic revision --autogenerate -m "message"
alembic upgrade head
```

---

## 🐳 Run all service with Docker

### 1. Development mode

#### Build images

```bash
docker compose -f docker-compose.dev.yaml build
```

#### Start containers

```bash
docker compose -f docker-compose.dev.yaml up
```

* FastAPI backend: [http://localhost:8000](http://localhost:8000)
* Streamlit UI: [http://localhost:8501](http://localhost:8501)
* PostgreSQL: [http://localhost:5432](http://localhost:5432)
* Redis: [http://localhost:6379](http://localhost:6379)

* Healthcheck for Backend: [http://localhost:8000/health](http://localhost:8000/health)
* Healthcheck for all services: `make healthcheck-dev`

#### DB migrations

```bash
make db-migrate-dev
make db-upgrade-dev
```

#### Stop containers

```bash
docker-compose down
```

### 2. Production mode

#### Build images

```bash
docker compose -f docker-compose.prod.yaml build
```

#### Start containers

```bash
docker compose -f docker-compose.prod.yaml up -d
```

* Healthcheck for Backend: [http://localhost:8000/health](http://localhost:8000/health)
* Healthcheck for all services: `make healthcheck-prod`

#### DB migrations

```bash
make db-migrate-prod
make db-upgrade-prod
```

---

## 🛠 Make File CMD

### Development

```makefile
make build-dev        # Build dev images
make up-dev           # Start dev containers
make deploy-dev       # Rebuild and start containers
make healthcheck-dev  # Check service health
make db-migrate-dev   # Create DB migration with timestamp
make db-upgrade-dev   # Apply latest DB migration
make bash-dev         # Open shell inside backend container
make logs-dev         # Show logs
```

### Production

```makefile
make build-prod
make up-prod
make deploy-prod
make healthcheck-prod
make db-migrate-prod
make db-upgrade-prod
make bash-prod
make logs-prod
```

---

## 🤝 Contributing

We welcome contributions of all kinds!
Feel free to fork the repo, submit issues, or open a pull request.

---

## 📄 License

This project is licensed under the **MIT License**.