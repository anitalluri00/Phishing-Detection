pipeline {
  agent any

  options {
    timestamps()
    disableConcurrentBuilds()
  }

  parameters {
    booleanParam(name: "DOWNLOAD_KAGGLE_DATASETS", defaultValue: false, description: "Download configured Kaggle datasets before training.")
    booleanParam(name: "TRAIN_MODEL", defaultValue: true, description: "Train model internally using local dataset.")
    booleanParam(name: "SECURITY_AUDIT", defaultValue: true, description: "Run dependency vulnerability scan.")
    booleanParam(name: "PUSH_IMAGES", defaultValue: false, description: "Push images to Docker registry.")
    booleanParam(name: "DEPLOY_TO_K8S", defaultValue: false, description: "Deploy after build.")
    string(name: "DOCKER_REGISTRY", defaultValue: "", description: "Registry prefix, e.g. docker.io/your-user")
    string(name: "IMAGE_TAG", defaultValue: "", description: "Image tag; empty uses build-<BUILD_NUMBER>")
    string(name: "DOCKER_REGISTRY_CREDENTIALS_ID", defaultValue: "docker-registry-creds", description: "Jenkins username/password credentials id")
    string(name: "KUBECONFIG_CREDENTIALS_ID", defaultValue: "kubeconfig", description: "Jenkins file credentials id for kubeconfig")
    string(name: "K8S_NAMESPACE", defaultValue: "phishing-detection", description: "Kubernetes namespace")
    string(name: "KAGGLE_API_TOKEN_CREDENTIALS_ID", defaultValue: "kaggle-api-token", description: "Jenkins secret text credentials id")
  }

  environment {
    BACKEND_NAME = "phishing-backend"
    FRONTEND_NAME = "phishing-frontend"
  }

  stages {
    stage("Checkout") {
      steps { checkout scm }
    }

    stage("Init") {
      steps {
        script {
          env.RESOLVED_TAG = params.IMAGE_TAG?.trim() ? params.IMAGE_TAG.trim() : "build-${env.BUILD_NUMBER}"
          env.LOCAL_BACKEND_IMAGE = "${env.BACKEND_NAME}:${env.RESOLVED_TAG}"
          env.LOCAL_FRONTEND_IMAGE = "${env.FRONTEND_NAME}:${env.RESOLVED_TAG}"

          if (params.DOCKER_REGISTRY?.trim()) {
            env.REG_BACKEND_IMAGE = "${params.DOCKER_REGISTRY.trim()}/${env.BACKEND_NAME}:${env.RESOLVED_TAG}"
            env.REG_FRONTEND_IMAGE = "${params.DOCKER_REGISTRY.trim()}/${env.FRONTEND_NAME}:${env.RESOLVED_TAG}"
          } else {
            env.REG_BACKEND_IMAGE = ""
            env.REG_FRONTEND_IMAGE = ""
          }

          env.DEPLOY_BACKEND_IMAGE = params.PUSH_IMAGES ? env.REG_BACKEND_IMAGE : env.LOCAL_BACKEND_IMAGE
          env.DEPLOY_FRONTEND_IMAGE = params.PUSH_IMAGES ? env.REG_FRONTEND_IMAGE : env.LOCAL_FRONTEND_IMAGE
        }
      }
    }

    stage("Backend Checks") {
      steps {
        sh """
          set -euo pipefail
          python3 --version
          python3 -m py_compile backend/app.py backend/feature_extraction.py backend/train_model.py
        """
      }
    }

    stage("Install Python Dependencies") {
      steps {
        sh """
          set -euo pipefail
          python3 -m venv .venv
          . .venv/bin/activate
          python -m pip install --upgrade pip
          pip install -r requirements.txt
        """
      }
    }

    stage("Dependency Vulnerability Scan") {
      when { expression { return params.SECURITY_AUDIT } }
      steps {
        sh """
          set -euo pipefail
          . .venv/bin/activate
          pip install pip-audit
          pip-audit -r backend/requirements.txt
        """
      }
    }

    stage("Download Kaggle Datasets") {
      when { expression { return params.DOWNLOAD_KAGGLE_DATASETS } }
      steps {
        withCredentials([string(credentialsId: params.KAGGLE_API_TOKEN_CREDENTIALS_ID, variable: "KAGGLE_API_TOKEN")]) {
          sh """
            set -euo pipefail
            . .venv/bin/activate
            python tools/download_kaggle_datasets.py
          """
        }
      }
    }

    stage("Train Model") {
      when { expression { return params.TRAIN_MODEL } }
      steps {
        sh """
          set -euo pipefail
          . .venv/bin/activate
          python backend/train_model.py --input-csv data/urldata.csv --output-model backend/model/model.pkl --output-metrics backend/model/metrics.json
        """
      }
    }

    stage("Build Images") {
      steps {
        sh """
          set -euo pipefail
          docker build -t "${LOCAL_BACKEND_IMAGE}" -f backend/Dockerfile backend
          docker build -t "${LOCAL_FRONTEND_IMAGE}" -f frontend/Dockerfile frontend
        """
      }
    }

    stage("Push Images") {
      when { expression { return params.PUSH_IMAGES } }
      steps {
        script {
          if (!params.DOCKER_REGISTRY?.trim()) {
            error("PUSH_IMAGES=true requires DOCKER_REGISTRY.")
          }
        }
        withCredentials([usernamePassword(credentialsId: params.DOCKER_REGISTRY_CREDENTIALS_ID, usernameVariable: "REGISTRY_USER", passwordVariable: "REGISTRY_PASS")]) {
          sh """
            set -euo pipefail
            REGISTRY_HOST="\$(echo "${params.DOCKER_REGISTRY}" | cut -d/ -f1)"
            echo "\${REGISTRY_PASS}" | docker login "\${REGISTRY_HOST}" -u "\${REGISTRY_USER}" --password-stdin
            docker tag "${LOCAL_BACKEND_IMAGE}" "${REG_BACKEND_IMAGE}"
            docker tag "${LOCAL_FRONTEND_IMAGE}" "${REG_FRONTEND_IMAGE}"
            docker push "${REG_BACKEND_IMAGE}"
            docker push "${REG_FRONTEND_IMAGE}"
            docker logout "\${REGISTRY_HOST}"
          """
        }
      }
    }

    stage("Deploy") {
      when { expression { return params.DEPLOY_TO_K8S } }
      steps {
        withCredentials([file(credentialsId: params.KUBECONFIG_CREDENTIALS_ID, variable: "KUBECONFIG_FILE")]) {
          sh """
            set -euo pipefail
            export KUBECONFIG="${KUBECONFIG_FILE}"

            kubectl apply -f infra/k8s/namespace.yaml
            kubectl apply -f infra/k8s/backend.yaml
            kubectl apply -f infra/k8s/frontend.yaml

            kubectl -n "${params.K8S_NAMESPACE}" set image deployment/backend backend="${DEPLOY_BACKEND_IMAGE}"
            kubectl -n "${params.K8S_NAMESPACE}" set image deployment/frontend frontend="${DEPLOY_FRONTEND_IMAGE}"

            kubectl -n "${params.K8S_NAMESPACE}" rollout status deployment/backend --timeout=240s
            kubectl -n "${params.K8S_NAMESPACE}" rollout status deployment/frontend --timeout=240s
          """
        }
      }
    }
  }

  post {
    always {
      sh "docker image prune -f || true"
    }
  }
}
