#!/bin/python3
"""
Kociemba Frontier — GCP Cloud Run Deployment
Builds container, pushes to GCR, deploys to Cloud Run.
"""
import subprocess, sys, json, os

PROJECT = "evez666"
REGION = "us-central1"
SERVICE = "kociemba-frontier"
IMAGE = f"us-docker.pkg.dev/{PROJECT}/evez/frontier:latest"
DIR = os.path.dirname(os.path.abspath(__file__))

def run(cmd, **kw):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print(f"✗ {cmd}\n{r.stderr}")
        return None
    return r.stdout

print("═══ KOCIMBA FRONTIER — GCP Deploy ═══")

# 1. Set project
if run(f"gcloud config set project {PROJECT}"):
    print(f"✅ Project: {PROJECT}")

# 2. Enable APIs
apis = ["run", "cloudbuild", "containerregistry", "artifactregistry"]
for api in apis:
    run(f"gcloud services enable {api}.googleapis.com")
print("✅ APIs enabled")

# 3. Create repository if needed
run(f"gcloud artifacts repositories create evez --repository-format=docker --location={REGION} 2>/dev/null")

# 4. Write Dockerfile
DOCKERFILE = """
FROM nginx:alpine
COPY index.html /usr/share/nginx/html/index.html
COPY app.js /usr/share/nginx/html/app.js
COPY style.css /usr/share/nginx/html/style.css
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
""".strip()

with open(f"{DIR}/Dockerfile", "w") as f:
    f.write(DOCKERFILE)

# 5. Build and push
print("🔨 Building container...")
out = run(f"gcloud builds submit --tag {IMAGE} {DIR}", timeout=300)
if out:
    print(f"✅ Image pushed: {IMAGE}")

# 6. Deploy to Cloud Run
print("🚀 Deploying to Cloud Run...")
deploy = run(f"gcloud run deploy {SERVICE} --image {IMAGE} --region {REGION} --platform managed --allow-unauthenticated", timeout=120)
if deploy:
    # Extract URL
    for line in deploy.split("\n"):
        if "URL:" in line or "https://" in line:
            print(f"✅ LIVE: {line.strip()}")
            with open(f"{DIR}/.deploy-url", "w") as f:
                f.write(line.strip())
            break

print("\n═══ DEPLOYMENT COMPLETE ═══")
print("Run `cat .deploy-url` to get the live URL")
