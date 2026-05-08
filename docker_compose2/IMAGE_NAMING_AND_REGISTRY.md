# Docker Image Naming, Private Registries, and Professional Workflow

This document covers how Docker image names work, how to push images to private repositories, how professionals manage changes across multiple services, and the general syntax patterns you need to know — not just for one project but for any stack.

---

## 1. How Docker Image Names Actually Work

Every Docker image name follows a structured format. Understanding the anatomy of a name tells you exactly where an image lives and how to pull or push it.

### Full syntax

```
[registry/][namespace/]repository[:tag]
```

| Part | What it is | Example |
|---|---|---|
| `registry` | The server hosting the image. Omit = Docker Hub. | `docker.io`, `ghcr.io`, `123456789.dkr.ecr.us-east-1.amazonaws.com` |
| `namespace` | Your Docker Hub username or org name. | `darkemperor6`, `mycompany` |
| `repository` | The actual image name, usually the app/service name. | `app-myapp`, `mongo`, `nginx` |
| `tag` | A label for a specific version. Omit = `latest` (not recommended in production). | `1.0.1`, `2.3.0-alpine`, `stable` |

### Real examples broken down

```
darkemperor6/app-myapp:1.0.1
│            │         │
│            │         └─ tag: version 1.0.1
│            └─ repository: app-myapp
└─ namespace: darkemperor6 (your Docker Hub username)

mongo:8.0.21
│     │
│     └─ tag: 8.0.21
└─ repository: mongo (official image, no namespace needed)

ghcr.io/mycompany/backend-api:v2.1.0
│        │          │           │
│        │          │           └─ tag
│        │          └─ repository
│        └─ namespace (org on GitHub)
└─ registry: GitHub Container Registry
```

### Why `latest` is dangerous in production

When you write `image: mongo` or `image: mongo:latest`, Docker will pull whatever the current latest version is. If a breaking change ships in a new version, your stack breaks. Always pin exact versions:

```yaml
# Bad — unpredictable
image: mongo

# Good — locked to a specific version
image: mongo:8.0.21
```

### Tag conventions professionals use

| Convention | Example | When used |
|---|---|---|
| Semantic version | `1.0.1`, `2.3.0` | Standard app releases |
| Git commit SHA | `a3f8c91` | CI/CD pipelines (exact traceability) |
| Branch name | `main`, `develop` | Staging environments |
| Environment | `prod`, `staging` | Multi-environment deployments |
| Combined | `1.0.1-alpine`, `2.0.0-prod` | Variant + version |

---

## 2. Public vs. Private Registries

### What is a registry?

A registry is a server that stores Docker images. When you run `docker pull mongo:8.0.21`, Docker contacts Docker Hub and downloads that image. When you push an image, you upload it to a registry.

### Registry types

| Registry | Type | URL | Best for |
|---|---|---|---|
| Docker Hub | Public / Private | `hub.docker.com` | Default, personal projects |
| GitHub Container Registry | Public / Private | `ghcr.io` | Projects hosted on GitHub |
| AWS ECR | Private | `*.dkr.ecr.*.amazonaws.com` | AWS deployments |
| Google Artifact Registry | Private | `*.pkg.dev` | GCP deployments |
| Azure Container Registry | Private | `*.azurecr.io` | Azure deployments |
| Self-hosted (Harbor, Nexus) | Private | Your own domain | Air-gapped / on-prem |

### When you need a private registry

- Your image contains proprietary code you do not want public
- Your team needs access to images without making them publicly discoverable
- You want access controls (only specific users or CI pipelines can push/pull)
- Compliance requires keeping images within a specific cloud account

---

## 3. Prerequisites and Initial Setup

### Prerequisites

Before you can push images to any registry, you need:

1. **Docker Desktop / Docker Engine installed** and running
2. **An account** on the registry you are using (Docker Hub, GitHub, AWS, etc.)
3. **Docker CLI authenticated** to that registry
4. **Your image named correctly** to match the registry and namespace

### Setting up Docker Hub (step by step)

**Step 1 — Create a Docker Hub account**

Go to [hub.docker.com](https://hub.docker.com) and create a free account. Your username becomes your namespace for all image names.

**Step 2 — Create a repository on Docker Hub**

On Docker Hub, click **Repositories → Create Repository**. Set it to **Private**. Name it something that matches your image (e.g., `app-myapp`).

**Step 3 — Log in from the terminal**

```bash
docker login
```

You will be prompted for your Docker Hub username and password. For better security, use an access token instead of your password:

1. On Docker Hub go to **Account Settings → Security → New Access Token**
2. Give it a name (e.g., `my-laptop`) and copy the token
3. Use the token as the password when prompted

```bash
docker login
Username: darkemperor6
Password: <paste your access token here>
```

On success you see:

```
Login Succeeded
```

Docker stores credentials locally in `~/.docker/config.json`. You only need to log in once per machine.

**Step 4 — Log in to a non-Docker-Hub registry (general syntax)**

```bash
# GitHub Container Registry
docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin <<< YOUR_TOKEN

# AWS ECR (uses AWS CLI)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com

# Azure ACR
az acr login --name myregistry

# Self-hosted
docker login registry.mycompany.com -u myuser -p mypassword
```

---

## 4. Building and Tagging Images

### Build with a name directly

The cleanest approach is to name the image at build time using `-t`:

```bash
# General syntax
docker build -t [registry/]namespace/repository:tag path/to/dockerfile/folder

# Docker Hub example
docker build -t darkemperor6/app-myapp:1.0.1 .

# GitHub Container Registry example
docker build -t ghcr.io/darkemperor6/app-myapp:1.0.1 .

# AWS ECR example
docker build -t 123456789.dkr.ecr.us-east-1.amazonaws.com/app-myapp:1.0.1 .
```

The `.` at the end means "use the Dockerfile in the current folder".

### Tag an existing image for a different registry

If you already built an image under one name and want to push it to another registry, use `docker tag`:

```bash
# General syntax
docker tag SOURCE_IMAGE[:TAG] TARGET_IMAGE[:TAG]

# Example: re-tag a local image for Docker Hub
docker tag myapp:local darkemperor6/app-myapp:1.0.1

# Example: re-tag the same image for AWS ECR
docker tag myapp:local 123456789.dkr.ecr.us-east-1.amazonaws.com/app-myapp:1.0.1
```

`docker tag` does not copy anything — it just creates a second name pointing to the same image layers.

### Tagging with multiple tags at once

```bash
# Build once, tag as both a version and latest
docker build -t darkemperor6/app-myapp:1.0.1 -t darkemperor6/app-myapp:latest .
```

---

## 5. Pushing Images to a Private Repository

### Push syntax (general)

```bash
docker push [registry/]namespace/repository:tag
```

### Push to Docker Hub

```bash
# Push a specific version
docker push darkemperor6/app-myapp:1.0.1

# Push the latest tag too (if you tagged both)
docker push darkemperor6/app-myapp:latest
```

Docker pushes only the layers that don't already exist in the registry — subsequent pushes are fast because only changed layers are uploaded.

### Push to GitHub Container Registry

```bash
docker push ghcr.io/darkemperor6/app-myapp:1.0.1
```

### Push to AWS ECR

```bash
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/app-myapp:1.0.1
```

### What happens during a push

```
The push refers to repository [docker.io/darkemperor6/app-myapp]
a3f8c9123456: Pushed          ← your app layer
b7d9e2345678: Layer already exists  ← node_modules layer (cached from previous push)
c1a2b3456789: Layer already exists  ← base node image (already on Hub)
1.0.1: digest: sha256:abc123... size: 1234
```

Each line is a layer. Layers that haven't changed are skipped — this is Docker's layer caching working for you on push too.

---

## 6. Using the Private Image in docker-compose

Once your image is pushed, you reference it by its full name in the compose file. This is exactly what your `mongo.yaml` already does:

```yaml
services:
  myapp:
    image: darkemperor6/app-myapp:1.0.1   # ← full private image name
    ports:
      - 3000:3000
```

When another machine (your colleague, a CI server, a cloud VM) runs `docker compose up`, Docker sees this name, checks locally, and if not found it automatically pulls from the registry. If the registry is private, that machine must be logged in first.

---

## 7. How Professionals Handle Multiple Services

This is the most practically important section. In a real stack you have many images — your app, a database, an admin UI, a cache, a queue, etc. Each one has its own versioning lifecycle and its own rules.

### The core principle: separate concerns

You do not bump a version number just because something else changed. Each service version tracks only the changes to that service.

| Service | Changed? | What you do |
|---|---|---|
| `myapp` | Yes — code fix | Build and push new tag, update compose |
| `mongo` | No | Leave it as `mongo:8.0.21` |
| `mongo-express` | No | Leave it as `mongo-express:1.0.2` |

### Your compose file as the single source of truth

The compose file is the contract for what versions of every service are running together. Treat it like a lockfile.

```yaml
version: '3'
services:

  myapp:
    build: .
    image: darkemperor6/app-myapp:1.0.1     # YOUR image — you control this
    ports:
      - 3000:3000
    depends_on:
      - mongo

  mongo:
    image: mongo:8.0.21                      # OFFICIAL image — pin exact version
    ports:
      - 27017:27017
    environment:
      - MONGO_INITDB_ROOT_USERNAME=gloriousadmin
      - MONGO_INITDB_ROOT_PASSWORD=ingloriouslies

  mongo-express:
    image: mongo-express:1.0.2               # OFFICIAL image — pin exact version
    ports:
      - 8081:8081
    environment:
      - ME_CONFIG_MONGODB_ADMINUSERNAME=gloriousadmin
      - ME_CONFIG_MONGODB_ADMINPASSWORD=ingloriouslies
      - ME_CONFIG_MONGODB_URL=mongodb://gloriousadmin:ingloriouslies@mongo:27017
    depends_on:
      - mongo
```

### Scenario: you changed your app code

Only `myapp` changed. The workflow:

```bash
# 1. Build and tag the new version
docker build -t darkemperor6/app-myapp:1.0.2 .

# 2. Push it to the private registry
docker push darkemperor6/app-myapp:1.0.2

# 3. Update the image tag in mongo.yaml
#    Change: image: darkemperor6/app-myapp:1.0.1
#    To:     image: darkemperor6/app-myapp:1.0.2

# 4. Restart only the changed service
docker compose -f mongo.yaml up -d --no-deps myapp
```

`--no-deps` restarts only `myapp` without touching `mongo` or `mongo-express`. This is important — you do not want to restart your database just because you changed the app.

### Scenario: you want to upgrade MongoDB

MongoDB releases a new version you want. Only `mongo` changes.

```bash
# 1. Test the new version locally first
#    In mongo.yaml, change mongo image to mongo:8.1.0 (or whatever new version)

# 2. Pull the new image and recreate only mongo
docker compose -f mongo.yaml pull mongo
docker compose -f mongo.yaml up -d --no-deps mongo

# 3. Watch the logs to confirm it started correctly
docker compose -f mongo.yaml logs -f mongo
```

`docker compose pull` fetches the latest version of a service's image from the registry without restarting anything. Then `up -d --no-deps` applies it.

### Scenario: you want to upgrade mongo-express

Same as above but targeting `mongo-express`:

```bash
docker compose -f mongo.yaml pull mongo-express
docker compose -f mongo.yaml up -d --no-deps mongo-express
```

### Scenario: everything needs to restart (deployment to a new server)

On a fresh server where nothing exists yet:

```bash
# 1. Log in to the private registry (required for your custom image)
docker login

# 2. Pull all images before starting (optional but recommended to check for errors)
docker compose -f mongo.yaml pull

# 3. Start the full stack
docker compose -f mongo.yaml up -d

# 4. Verify everything is running
docker compose -f mongo.yaml ps
```

### Targeting individual services — general syntax

```bash
# Restart one service only (stops and recreates the container)
docker compose -f mongo.yaml restart <service-name>

# Recreate one service with updated image, skip dependencies
docker compose -f mongo.yaml up -d --no-deps <service-name>

# Pull image for one service only
docker compose -f mongo.yaml pull <service-name>

# View logs for one service
docker compose -f mongo.yaml logs -f <service-name>

# Stop one service without removing it
docker compose -f mongo.yaml stop <service-name>

# Start a stopped service
docker compose -f mongo.yaml start <service-name>

# Run a one-off command inside a service
docker compose -f mongo.yaml exec <service-name> <command>
```

---

## 8. General Syntax Reference

This section gives you the abstract syntax for every major operation so you can apply it to any project, not just this one.

### Building images

```bash
# Build from Dockerfile in current directory
docker build -t NAMESPACE/REPOSITORY:TAG .

# Build from Dockerfile in a specific folder
docker build -t NAMESPACE/REPOSITORY:TAG ./path/to/context

# Build with a custom Dockerfile name
docker build -f path/to/Dockerfile -t NAMESPACE/REPOSITORY:TAG .

# Build targeting a specific stage in a multi-stage Dockerfile
docker build --target STAGE_NAME -t NAMESPACE/REPOSITORY:TAG .
```

### Tagging images

```bash
# Tag an existing image under a new name
docker tag SOURCE:TAG DESTINATION:TAG

# Add a second tag to the same image
docker tag NAMESPACE/REPOSITORY:1.0.0 NAMESPACE/REPOSITORY:latest
```

### Pushing and pulling

```bash
# Push to registry
docker push NAMESPACE/REPOSITORY:TAG

# Pull from registry
docker pull NAMESPACE/REPOSITORY:TAG

# Pull all service images in a compose file
docker compose -f FILE.yaml pull

# Pull one service's image
docker compose -f FILE.yaml pull SERVICE_NAME
```

### Authenticating to registries

```bash
# Docker Hub (interactive)
docker login

# Docker Hub (non-interactive, for scripts/CI)
echo "TOKEN" | docker login --username USERNAME --password-stdin

# Any registry
docker login REGISTRY_URL

# Log out
docker logout REGISTRY_URL
```

### Running containers from private images

```bash
# Docker will pull automatically if not cached
docker run -d -p HOST_PORT:CONTAINER_PORT NAMESPACE/REPOSITORY:TAG

# With environment variables
docker run -d \
  -e ENV_VAR=value \
  -p HOST_PORT:CONTAINER_PORT \
  NAMESPACE/REPOSITORY:TAG
```

### Compose — general service operations

```bash
# Start all services
docker compose -f FILE.yaml up -d

# Start all services and force rebuild of built images
docker compose -f FILE.yaml up -d --build

# Stop all services (containers remain, can be restarted)
docker compose -f FILE.yaml stop

# Stop and remove containers + network (images kept)
docker compose -f FILE.yaml down

# Stop and remove containers + network + volumes (data gone)
docker compose -f FILE.yaml down -v

# Stop and remove containers + network + images
docker compose -f FILE.yaml down --rmi all

# Check status of all services
docker compose -f FILE.yaml ps

# Stream logs from all services
docker compose -f FILE.yaml logs -f

# Stream logs from a specific service
docker compose -f FILE.yaml logs -f SERVICE_NAME
```

---

## 9. Professional Practices

### Never use `latest` for anything you deploy

`latest` is resolved at pull time. Two machines pulling at different moments may get different actual versions. Pin every image to an exact version and update deliberately.

### One repository per service

Do not stuff multiple apps into one Docker repository. Give each service its own repository: `darkemperor6/app-myapp`, `darkemperor6/backend-api`, `darkemperor6/worker`, etc.

### Semantic versioning for your own images

Follow the pattern `MAJOR.MINOR.PATCH`:

- `PATCH` — bug fix, no behaviour change (`1.0.0` → `1.0.1`)
- `MINOR` — new feature, backwards compatible (`1.0.1` → `1.1.0`)
- `MAJOR` — breaking change (`1.1.0` → `2.0.0`)

This lets anyone reading your compose file understand the nature of a change at a glance.

### Store your compose file in version control

Your `mongo.yaml` is already in the project. Commit it. The file is the authoritative record of which version of every service is deployed. A git log of the compose file is your deployment history.

### Use `.env` files for secrets, not hardcoded values

Hardcoding credentials into the compose file (as in the current project) is fine for learning but not for production. The professional pattern uses a `.env` file:

```bash
# .env  (never commit this file — add it to .gitignore)
MONGO_USERNAME=gloriousadmin
MONGO_PASSWORD=ingloriouslies
```

```yaml
# mongo.yaml
services:
  mongo:
    image: mongo:8.0.21
    environment:
      - MONGO_INITDB_ROOT_USERNAME=${MONGO_USERNAME}
      - MONGO_INITDB_ROOT_PASSWORD=${MONGO_PASSWORD}
```

Docker Compose automatically reads `.env` from the same directory as the compose file.

### Build once, push once, pull everywhere

The workflow is:

```
Developer machine  →  docker build  →  docker push  →  Registry
                                                            ↓
                              Production server  →  docker pull  →  docker compose up
```

You never build on production. The production machine only pulls images. This guarantees that what runs in production is exactly what you tested locally.

### Use build arguments for environment-specific images

If your image needs slight differences between environments (e.g., a dev image with debug tools), use build args:

```dockerfile
# Dockerfile
ARG NODE_ENV=production
ENV NODE_ENV=${NODE_ENV}
```

```bash
# Build a dev variant
docker build --build-arg NODE_ENV=development -t darkemperor6/app-myapp:1.0.1-dev .

# Build a prod variant (default)
docker build -t darkemperor6/app-myapp:1.0.1 .
```

### Pull policy in compose

By default, Compose does not re-pull images that are already cached locally. To always pull the latest version of pinned images:

```bash
docker compose -f mongo.yaml pull && docker compose -f mongo.yaml up -d
```

Or set the pull policy in the compose file:

```yaml
services:
  myapp:
    image: darkemperor6/app-myapp:1.0.1
    pull_policy: always    # always pull even if cached
```

| Policy | Behaviour |
|---|---|
| `missing` | Pull only if the image is not in the local cache (default) |
| `always` | Always pull before starting |
| `never` | Never pull — fail if image is not cached |
| `build` | Build locally if a `build:` section exists |

---

## 10. Full End-to-End Professional Workflow (This Project)

Here is the complete workflow from code change to updated running stack, using your actual project as an example.

### Step 1 — Make your change

Edit `server.js`, `index.html`, or whatever changed.

### Step 2 — Increment the version

Decide which version bump applies. Say `1.0.1` → `1.0.2`.

### Step 3 — Build the new image

```bash
cd d:\docker_practice\docker_compose2\app
docker build -t darkemperor6/app-myapp:1.0.2 .
```

### Step 4 — Test it locally

```bash
docker compose -f mongo.yaml up -d --build
# verify http://localhost:3000 works as expected
docker compose -f mongo.yaml down
```

### Step 5 — Push to the private registry

```bash
docker push darkemperor6/app-myapp:1.0.2
```

### Step 6 — Update mongo.yaml

Change the image line in `mongo.yaml`:

```yaml
myapp:
  build: .
  image: darkemperor6/app-myapp:1.0.2   # bumped from 1.0.1
```

### Step 7 — Commit mongo.yaml to version control

```bash
git add mongo.yaml
git commit -m "deploy: bump app-myapp to 1.0.2"
```

### Step 8 — Deploy

On the target server (or to update the running local stack):

```bash
docker compose -f mongo.yaml up -d --no-deps myapp
```

Only `myapp` restarts. `mongo` and `mongo-express` are untouched.

---

## Summary Table

| Task | Command |
|---|---|
| Log in to Docker Hub | `docker login` |
| Build and tag image | `docker build -t namespace/repo:tag .` |
| Push to registry | `docker push namespace/repo:tag` |
| Pull from registry | `docker pull namespace/repo:tag` |
| Start full stack | `docker compose -f FILE.yaml up -d` |
| Restart one service only | `docker compose -f FILE.yaml up -d --no-deps SERVICE` |
| Pull updated image for one service | `docker compose -f FILE.yaml pull SERVICE` |
| View live logs for one service | `docker compose -f FILE.yaml logs -f SERVICE` |
| Stop full stack | `docker compose -f FILE.yaml down` |
| Check running services | `docker compose -f FILE.yaml ps` |
