# PhishDetect (URL + Infra + CI/CD)

This repository contains:
- A hardened Flask backend API for phishing URL prediction.
- A separate frontend (Nginx static app) that calls backend `/api/predict`.
- Model training scripts.
- Kaggle dataset download script using `kagglehub`.
- Docker, Kubernetes, Terraform, and Jenkins CI/CD setup.

## Folder Structure

```text
.
├── backend
│   ├── app.py
│   ├── feature_extraction.py
│   ├── train_model.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── model/
│   └── templates/
├── frontend
│   ├── src/
│   ├── nginx/default.conf.template
│   └── Dockerfile
├── infra
│   ├── k8s/
│   └── terraform/
├── tools
│   └── download_kaggle_datasets.py
├── data
│   └── urldata.csv
└── Jenkinsfile
```

## 1) Python Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) Kaggle Dataset Download (as requested)

The downloader script includes all dataset IDs you listed.

Do not hardcode tokens in source files. Export it only in your shell/session:

```bash
export KAGGLE_API_TOKEN="<your-kaggle-token>"
python3 tools/download_kaggle_datasets.py
```

Downloaded path mappings are saved to:
- `data/kaggle/download_map.json`

## 3) Train Model Internally

Train from engineered dataset:

```bash
python3 backend/train_model.py \
  --input-csv data/urldata.csv \
  --output-model backend/model/model.pkl \
  --output-metrics backend/model/metrics.json
```

## 4) Run Backend Locally

```bash
python3 backend/app.py
```

Endpoints:
- `GET /health`
- `POST /api/predict` with JSON body `{"url":"https://example.com"}`

## 5) Docker

Build:

```bash
docker build -f backend/Dockerfile -t phishing-backend:latest backend
docker build -f frontend/Dockerfile -t phishing-frontend:latest frontend
```

Run:

```bash
docker network create phishing-net
docker run -d --name backend --network phishing-net -p 5000:5000 phishing-backend:latest
docker run -d --name frontend --network phishing-net -e BACKEND_UPSTREAM=http://backend:5000 -p 8080:8080 phishing-frontend:latest
```

## 6) Kubernetes

```bash
kubectl apply -f infra/k8s/namespace.yaml
kubectl apply -f infra/k8s/backend.yaml
kubectl apply -f infra/k8s/frontend.yaml
```

## 7) Terraform

```bash
cd infra/terraform
terraform init
terraform apply
```

### Automatic `kubectl apply` on `terraform apply`

Terraform is configured to automatically run:

```bash
kubectl apply -f infra/k8s/namespace.yaml
kubectl apply -f infra/k8s/backend.yaml
kubectl apply -f infra/k8s/frontend.yaml
```

Controls:

```bash
# default: enabled
terraform apply

# disable auto kubectl apply
terraform apply -var="run_kubectl_apply=false"

# custom k8s manifest directory
terraform apply -var="k8s_manifest_dir=/absolute/path/to/k8s"
```

## 8) Jenkins CI/CD

`Jenkinsfile` is included at repo root.

Main stages:
- Checkout
- Backend syntax checks
- Install Python dependencies in `.venv`
- Optional dependency vulnerability scan (`pip-audit`)
- Optional Kaggle download
- Optional internal model training
- Docker image build
- Optional image push
- Optional Kubernetes deploy

Required Jenkins credentials:
- Docker registry creds (username/password): default id `docker-registry-creds`
- Kubeconfig file credential: default id `kubeconfig`
- Kaggle token secret text: default id `kaggle-api-token`

## 9) Security and Bug Fixes Included

- Request payload size limit.
- URL validation and SSRF-style local/private host blocking.
- Deprecated web traffic lookup is disabled by default to avoid false-positive bias.
  If you need it, set `ENABLE_WEB_TRAFFIC_LOOKUP=true`.
- URL fetch feature extraction now follows redirects manually and blocks private/local
  redirect targets to reduce SSRF risk.
- Non-root backend container runtime.
- Non-root frontend container runtime.
- K8s security context hardening (`runAsNonRoot`, dropped capabilities, no privilege escalation).
- Removed debug-mode style behavior in production paths.
