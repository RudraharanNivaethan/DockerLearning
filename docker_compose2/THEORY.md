# Docker + Docker Compose: Full Theory for This Project

This document explains every concept you encountered, from first principles to running the full stack, using your actual project files as examples.

---

## 1. The Core Problem Docker Solves

When you run a Node app on your machine, it works because Node is installed, the right version is available, and `npm install` has been run. On someone else's machine it might not work because they have a different Node version, different OS, missing packages.

Docker solves this by packaging the app together with its entire runtime environment into a **container**. The container runs the same way on any machine that has Docker installed.

---

## 2. Key Terms

| Term | What it is |
|---|---|
| **Image** | A snapshot/blueprint of an app and its environment. Read-only. |
| **Container** | A running instance of an image. Like a process spawned from the blueprint. |
| **Dockerfile** | A recipe that defines how to build an image. |
| **Docker Compose** | A tool that runs multiple containers together as one coordinated stack. |
| **docker build** | Reads a Dockerfile and produces an image. |
| **docker run** | Starts a container from an image. |
| **docker compose up** | Reads a compose file and starts all services defined in it. |

---

## 3. The Dockerfile Explained

Your `Dockerfile` (in `docker_compose2/app/`):

```dockerfile
FROM node:26.0.0

RUN mkdir -p /home/app

COPY . /home/app

WORKDIR /home/app

RUN npm install

CMD ["node", "server.js"]
```

Each line is a layer:

| Line | What it does |
|---|---|
| `FROM node:26.0.0` | Start from the official Node 26 image from Docker Hub. This already has Node and npm installed inside it. |
| `RUN mkdir -p /home/app` | Inside the image, create the folder `/home/app`. |
| `COPY . /home/app` | Copy all files from your current folder (on your machine) into `/home/app` inside the image. This includes `server.js`, `package.json`, `index.html`, etc. |
| `WORKDIR /home/app` | Set the working directory for all following commands. Like doing `cd /home/app`. |
| `RUN npm install` | Run `npm install` inside the image to install dependencies from `package.json`. This installs express, mongodb, body-parser into the image. |
| `CMD ["node", "server.js"]` | The default command to run when a container starts from this image. |

`RUN` executes during the **build** phase (building the image).  
`CMD` executes during the **run** phase (starting a container).

---

## 4. Building an Image Manually

```bash
docker build -t myapp:1.0.0 .
```

- `-t myapp:1.0.0` gives the image a name and tag.
- `.` means "look for the Dockerfile in the current folder".

After this, `myapp:1.0.0` exists as an image on your machine.

---

## 5. Running a Container Manually

```bash
docker run myapp:1.0.0
```

This starts the container. Your app prints:

```
app listening on port 3000!
```

But the app then crashes with:

```
MongoServerSelectionError: connect ECONNREFUSED 127.0.0.1:27017
```

This is the most important concept to understand.

---

## 6. Why `localhost` Fails Inside a Container

When your Node app runs inside a Docker container, it is isolated. Every container has its own network namespace. Inside the container:

- `localhost` (or `127.0.0.1`) means **that specific container itself**.
- It does NOT mean your Windows machine.
- It does NOT mean another container.

Your `server.js` had this URL for the MongoDB connection:

```js
let mongoUrlLocal = "mongodb://gloriousadmin:ingloriouslies@localhost:27017";
```

When used inside the container, this tells the app to connect to MongoDB at `localhost:27017` — which means inside the same container. MongoDB is not running inside the `myapp` container. That container only has Node and your app code. So the connection is refused.

This is why the original `docker run` crashed with `ECONNREFUSED`.

---

## 7. The Three MongoDB URLs in `server.js`

Your `server.js` already documents all three situations:

```js
// use when starting application locally with node command
let mongoUrlLocal = "mongodb://gloriousadmin:ingloriouslies@localhost:27017";

// use when starting application as a separate docker container
let mongoUrlDocker = "mongodb://gloriousadmin:ingloriouslies@host.docker.internal:27017";

// use when starting application as docker container, part of docker-compose
let mongoUrlDockerCompose = "mongodb://gloriousadmin:ingloriouslies@mongo:27017";
```

| URL variable | When to use it | How MongoDB is reached |
|---|---|---|
| `mongoUrlLocal` | Running `node server.js` directly on your machine, MongoDB also installed locally | `localhost` = your machine |
| `mongoUrlDocker` | Running `docker run myapp`, MongoDB running as a separate container | `host.docker.internal` = your Windows host machine (Docker Desktop special hostname) |
| `mongoUrlDockerCompose` | Running via `docker compose up`, MongoDB is a service in the same compose file | `mongo` = the service name, resolved via Docker's internal DNS |

---

## 8. Docker Networks and Service Name Resolution

When Docker Compose starts multiple services, it automatically creates a **shared virtual network** and connects all containers to it.

In your case:

```
Network app_default   Created
```

Inside this network, every container can reach every other container **by its service name**.

Your compose file defines three services: `myapp`, `mongo`, `mongo-express`.

Inside the `myapp` container, you can connect to MongoDB using the hostname `mongo` because Docker DNS resolves `mongo` to the IP address of the `mongo` container on the shared network.

This is why `mongoUrlDockerCompose` works:

```js
"mongodb://gloriousadmin:ingloriouslies@mongo:27017"
```

The string `mongo` here is not a magic word — it is the **service name** you defined in `mongo.yaml`. If you renamed the service to `database`, the URL would need to be `@database:27017`.

---

## 9. The Compose File Explained

Your `mongo.yaml`:

```yaml
version: '3'
services:
     myapp:
      build: .
      ports:
        - 3000:3000
      depends_on:
        - mongo

     mongo:
       image: mongo:8.0.21
       ports:
         - 27017:27017
       environment:
         - MONGO_INITDB_ROOT_USERNAME=gloriousadmin
         - MONGO_INITDB_ROOT_PASSWORD=ingloriouslies

     mongo-express:
       image: mongo-express:1.0.2
       ports:
         - 8081:8081
       environment:
         - ME_CONFIG_MONGODB_ADMINUSERNAME=gloriousadmin
         - ME_CONFIG_MONGODB_ADMINPASSWORD=ingloriouslies
         - ME_CONFIG_MONGODB_URL=mongodb://gloriousadmin:ingloriouslies@mongo:27017
       depends_on:
         - mongo
```

**Service: `myapp`**

| Key | Meaning |
|---|---|
| `build: .` | Build the image from the Dockerfile in the current folder (`.`). No prebuilt image needed. |
| `ports: - 3000:3000` | Map port 3000 on your machine to port 3000 inside the container. `HOST:CONTAINER`. |
| `depends_on: - mongo` | Start the `mongo` container before starting `myapp`. Important: this only waits for the container to start, not for MongoDB to be fully ready. |

**Service: `mongo`**

| Key | Meaning |
|---|---|
| `image: mongo:8.0.21` | Use the official MongoDB image from Docker Hub. No Dockerfile needed. |
| `ports: - 27017:27017` | Exposes MongoDB on your machine at port 27017. Useful if you want to connect to it with a Mongo client from your Windows machine. |
| `MONGO_INITDB_ROOT_USERNAME` | Creates an admin user on first start. |
| `MONGO_INITDB_ROOT_PASSWORD` | Sets that user's password. |

**Service: `mongo-express`**

A web UI for browsing MongoDB databases.

| Key | Meaning |
|---|---|
| `image: mongo-express:1.0.2` | Official mongo-express image. |
| `ports: - 8081:8081` | Access it at `http://localhost:8081` from your browser. |
| `ME_CONFIG_MONGODB_URL` | How mongo-express connects to MongoDB. Uses `@mongo:27017` — again, the service name. |

---

## 10. What `docker compose up` Actually Does (From Your Terminal)

When you ran:

```bash
docker compose -f mongo.yaml up
```

Here is what happened, step by step:

**Step 1 — Network created:**
```
Network app_default   Created
```
A private virtual network is created for all services to communicate on.

**Step 2 — Image built:**
```
[+] Building 7.8s (13/13) FINISHED
...
naming to docker.io/library/app-myapp:latest
```
Compose sees `build: .` for `myapp` and runs `docker build` automatically.

**Step 3 — All containers created:**
```
Container app-mongo-1         Created
Container app-myapp-1         Created
Container app-mongo-express-1 Created
```

**Step 4 — Startup order and race condition:**
```
myapp-1          | app listening on port 3000!
mongo-express-1  | Waiting for mongo:27017...
mongo-1          | MongoDB init process complete; ready for start up.
```

The `myapp` container started and printed its ready message. MongoDB was still initializing. `mongo-express` was retrying the connection every few seconds. This is the `depends_on` limitation — it does not wait for readiness, only for the container process to start.

**Step 5 — MongoDB fully starts and accepts connections:**
```
mongo-1  | Listening on 0.0.0.0:27017
mongo-1  | mongod startup complete
```

Notice `0.0.0.0:27017` — this means MongoDB is listening on all interfaces inside the container, making it reachable from other containers on the same Docker network.

**Step 6 — mongo-express connects successfully:**
```
mongo-express-1  | Mongo Express server listening at http://0.0.0.0:8081
```

**Step 7 — Your app connects to MongoDB:**
```
mongo-1  | Successfully authenticated ... user: gloriousadmin
```

The `myapp` container connected to `mongo:27017`, authenticated with the credentials from the URL, and the connection succeeded.

---

## 11. Port Mapping: Why You Can Access Services From Your Browser

Your Windows browser does not know about Docker's internal network. Port mapping bridges the gap.

```
- 3000:3000
```

This means: when a request arrives at port 3000 on your Windows machine (the host), forward it into port 3000 of the `myapp` container.

So `http://localhost:3000` in your browser → Windows port 3000 → Docker port mapping → `myapp` container port 3000.

Same for `8081:8081` → `http://localhost:8081` in your browser → `mongo-express` container port 8081.

---

## 12. Why You Don't Need `--build` Every Time

When you run:

```bash
docker compose -f mongo.yaml up
```

Compose checks if the `app-myapp:latest` image already exists. If it does, it reuses it. If it doesn't (first run, or you deleted it), it builds it automatically because of `build: .`.

You only need `--build` if you want to force a rebuild after changing your source code or Dockerfile:

```bash
docker compose -f mongo.yaml up --build
```

---

## 13. Why Docker Desktop Must Be Running

Docker on Windows with WSL 2 works like this:

- Your WSL terminal has the `docker` CLI command installed.
- But the actual Docker **engine** (the daemon that builds and runs containers) is provided by Docker Desktop running as a Windows process in the background.
- The `docker` CLI in WSL communicates with Docker Desktop's engine via a socket.

If Docker Desktop is closed, the engine is not running. Any `docker` command fails with:

```
The command 'docker' could not be found in this WSL 2 distro.
```

This is misleading — the CLI is found, but the engine it talks to is not running. Opening Docker Desktop starts the engine and the CLI works again.

---

## 14. Full Picture: How the Three Files Work Together

```
docker_compose2/app/
├── Dockerfile          <- How to build the myapp image
├── mongo.yaml          <- What containers to run and how to connect them
├── server.js           <- The Node app code that runs inside myapp container
├── package.json        <- Node dependencies (used by npm install in Dockerfile)
├── index.html          <- Served by the app
└── images/             <- Served by the app
```

The flow:

1. `docker compose -f mongo.yaml up` reads `mongo.yaml`.
2. For `myapp`, it reads `Dockerfile` and builds the image.
3. The image contains: Node runtime + your app files + installed node_modules.
4. Compose creates a shared network and starts all three containers on it.
5. `myapp` connects to MongoDB using hostname `mongo` — resolved by Docker's internal DNS to the `mongo` container's IP on the shared network.
6. Your browser connects to the app via port mapping `localhost:3000 → container:3000`.

---

## 15. Quick Reference

| Task | Command |
|---|---|
| Start the full stack | `docker compose -f mongo.yaml up` |
| Start the stack and force rebuild | `docker compose -f mongo.yaml up --build` |
| Stop the stack | `Ctrl+C` in the terminal running compose |
| Stop and remove containers | `docker compose -f mongo.yaml down` |
| View running containers | `docker ps` |
| View all images | `docker images` |
| Remove an image | `docker rmi myapp:1.0.0` |
| Access the app | `http://localhost:3000` |
| Access mongo-express | `http://localhost:8081` |

---

## 16. The `depends_on` Caveat

`depends_on` only guarantees container **start order**, not service **readiness**.

Specifically:
- `myapp` will start after the `mongo` container process starts.
- But the `mongo` container's process is the MongoDB init script, which creates users, runs startup checks, and fully initializes before accepting connections. This takes a couple of seconds.
- If `myapp` tries to connect to MongoDB in that small window, it fails.

In your run, `myapp` printed `app listening on port 3000!` before MongoDB was ready. But the app only actually connects to MongoDB when a request hits `/get-profile` or `/update-profile`, not at startup. So by the time you made a request, MongoDB was already ready. That is why it worked.

If `myapp` connected to MongoDB at startup (e.g., in a startup health check), you would need a retry mechanism or a proper readiness check.

---

## 17. `.dockerignore`

### What it is

`.dockerignore` is a file you place in the same folder as your `Dockerfile`. It tells `docker build` which files and folders to **exclude from the build context** before anything is sent to the Docker engine.

### What the "build context" is

When you run:

```bash
docker build -t myapp:1.0.0 .
```

The `.` at the end means "use the current folder as the build context". Docker does not just read the Dockerfile — it packages up the entire folder and sends it to the Docker engine as a tar archive. This happens before any Dockerfile instruction runs.

Every file in that folder is included by default. Without a `.dockerignore`, this includes:

- `node_modules/` — potentially thousands of files and hundreds of megabytes
- `.git/` — your entire git history
- Editor files, logs, markdown docs, compose files

All of this gets sent even if `COPY` in the Dockerfile never touches it.

### Why this matters

**1. Slower builds**

Docker has to read, archive, and transfer all those files before the build even starts. A `node_modules` folder can be 200MB+. That is wasted time on every build.

**2. Larger images**

If your `COPY . /home/app` instruction copies files you don't need, they end up in the image layer permanently. Docker image layers are immutable — even if you `RUN rm -rf` them later, they still exist in the layer history and the image stays large.

**3. Cache invalidation**

Docker caches each layer. If the build context changes, the cache for the `COPY` step is busted and everything after it re-runs (including `npm install`). Files like `.git` change constantly, so without `.dockerignore` you lose the npm install cache more often than necessary.

**4. Security**

If you accidentally `COPY` a `.env` file with secrets, or a credentials file, it ends up baked into the image. If you push that image to Docker Hub, those secrets are public.

### Your `.dockerignore`

```
node_modules
.git
.gitignore
*.md
.dockerignore
mongo.yaml
```

Line by line:

| Entry | Why excluded |
|---|---|
| `node_modules` | The single most important entry. Your Dockerfile runs `RUN npm install` inside the image, which creates a fresh `node_modules` from `package.json`. Copying local `node_modules` in would override that with modules compiled for your machine's OS/architecture, which may not match the Linux container. Also massively bloats the build context. |
| `.git` | Git history, branches, and objects have no purpose inside a running container. Can be large and contains commit metadata you don't want in an image. |
| `.gitignore` | Tells git what to ignore — not relevant to the running application. |
| `*.md` | Documentation like `THEORY.md`. The app doesn't read these at runtime. Keeping them out keeps the image focused on only what is needed to run. |
| `.dockerignore` | The file itself has no reason to be inside the container. |
| `mongo.yaml` | The Docker Compose orchestration file. The container doesn't need to know how it was orchestrated. |

### What is intentionally NOT ignored

These files are required by the running app, so they are copied in:

| File/Folder | Why kept |
|---|---|
| `server.js` | The actual application code |
| `package.json` | Needed by `npm install` to know what to install |
| `index.html` | Served by the Express app at `/` |
| `images/` | Served by the Express app at `/profile-picture` |

### Syntax rules

`.dockerignore` uses the same pattern syntax as `.gitignore`:

| Pattern | Matches |
|---|---|
| `node_modules` | The `node_modules` folder at any level |
| `*.log` | Any file ending in `.log` |
| `**/*.test.js` | Any `.test.js` file in any subfolder |
| `!package.json` | Exception — do NOT ignore `package.json` even if a wider pattern would catch it |
| `temp/` | Only a folder named `temp`, not a file |

### Verifying what gets copied

You can see the build context size in the `docker build` output:

```
=> [internal] load build context
=> => transferring context: 3.55kB
```

In your actual build (from the terminal), the context was only **3.55kB** — because only the essential files were transferred. Before `.dockerignore` existed in the project, `COPY . /home/app` would have pulled in everything including any local `node_modules`.

### The difference between `.dockerignore` and not having `COPY` for a file

A common misunderstanding: "if I don't `COPY` a file in the Dockerfile, why does it matter if it's in the build context?"

The answer: the build context is packaged and sent to the Docker engine before any Dockerfile instruction runs. Even if the Dockerfile never references a file, it still gets transferred if it is not in `.dockerignore`. The transfer cost (time, network if using remote Docker) is paid regardless.

---

## 18. `mongo.yaml` — The Compose File in Depth

### What a Compose file is

A Compose file is a YAML file that describes a multi-container application. Instead of running several `docker run` commands manually with all their flags, you declare the entire stack once and start it with a single command.

Docker Compose reads the file and:
1. Creates a shared network for all services.
2. Builds any images that need building.
3. Pulls any images that need pulling.
4. Starts all containers in dependency order.

### The full file with annotations

```yaml
version: '3'
```

This key is obsolete in modern Compose. Docker warned about it in your terminal:
```
the attribute `version` is obsolete, it will be ignored
```
It was used in older versions to select which Compose feature set to use. Modern Compose ignores it entirely. It can be safely removed.

---

```yaml
services:
```

Everything under `services` is a service definition. Each service becomes one container (or multiple if scaled). Your file has three services: `myapp`, `mongo`, `mongo-express`.

---

### Service: `myapp`

```yaml
myapp:
  build: .
  ports:
    - 3000:3000
  depends_on:
    - mongo
```

**`build: .`**

Tells Compose to build the image from a Dockerfile. The `.` means "look in the current directory" — the same directory as `mongo.yaml`. Compose finds your `Dockerfile` there and runs the equivalent of:

```bash
docker build -t app-myapp:latest .
```

The image name `app-myapp` is auto-generated from the folder name (`app`) and the service name (`myapp`). This is why your terminal showed:

```
naming to docker.io/library/app-myapp:latest
```

Alternative syntax if you need to point to a different directory:

```yaml
build:
  context: ./some/other/folder
  dockerfile: MyDockerfile
```

**`ports: - 3000:3000`**

Format is `HOST_PORT:CONTAINER_PORT`.

- Left side (`3000`) — port on your Windows machine. You type this in your browser.
- Right side (`3000`) — port inside the container. Your app listens on this port (`app.listen(3000, ...)`).

These numbers don't have to match. If you wrote `8080:3000`, your browser would go to `localhost:8080` but the app inside the container still listens on `3000`. The mapping translates between the two.

Without `ports`, the service is only reachable from other containers on the same Docker network, not from your browser.

**`depends_on: - mongo`**

Guarantees that the `mongo` container is **started** before `myapp` starts. It does not wait for MongoDB to be ready to accept connections, only for the container process to exist. See Section 16 for the full explanation of this limitation.

---

### Service: `mongo`

```yaml
mongo:
  image: mongo:8.0.21
  ports:
    - 27017:27017
  environment:
    - MONGO_INITDB_ROOT_USERNAME=gloriousadmin
    - MONGO_INITDB_ROOT_PASSWORD=ingloriouslies
```

**`image: mongo:8.0.21`**

Uses a prebuilt image from Docker Hub. No `build` key, no Dockerfile needed. Compose pulls this image if it doesn't exist locally. `8.0.21` is the exact version tag. Using an exact version (not `latest`) means your stack is reproducible — it won't silently change if a new version is released.

**`ports: - 27017:27017`**

Exposes MongoDB on your Windows machine at port 27017. This is useful when you want to connect to MongoDB from outside Docker — for example, using MongoDB Compass (a GUI client) or `mongosh` from your WSL terminal. Without this, MongoDB is still reachable from other containers on the same network (via `mongo:27017`), but not from your browser or any tool running on your machine.

**`environment`**

These are environment variables passed into the container at startup. The MongoDB image reads these specific variable names during its init script to create an admin user on first run:

| Variable | Effect |
|---|---|
| `MONGO_INITDB_ROOT_USERNAME` | Creates a root user with this username |
| `MONGO_INITDB_ROOT_PASSWORD` | Sets this as the root user's password |

This only runs once — on the very first startup when the data directory is empty. After that, the user already exists in the database and these variables are ignored.

The credentials set here must match the credentials in your connection URL in `server.js`:

```js
"mongodb://gloriousadmin:ingloriouslies@mongo:27017"
```

If they don't match, authentication fails.

---

### Service: `mongo-express`

```yaml
mongo-express:
  image: mongo-express:1.0.2
  ports:
    - 8081:8081
  environment:
    - ME_CONFIG_MONGODB_ADMINUSERNAME=gloriousadmin
    - ME_CONFIG_MONGODB_ADMINPASSWORD=ingloriouslies
    - ME_CONFIG_MONGODB_URL=mongodb://gloriousadmin:ingloriouslies@mongo:27017
  depends_on:
    - mongo
```

mongo-express is a web-based UI for browsing and editing MongoDB data. It has no Dockerfile — it's a prebuilt image.

**`ME_CONFIG_MONGODB_ADMINUSERNAME` / `ME_CONFIG_MONGODB_ADMINPASSWORD`**

Credentials mongo-express uses to authenticate with MongoDB. Must match the admin user created by the `mongo` service.

**`ME_CONFIG_MONGODB_URL`**

The full connection string mongo-express uses to reach MongoDB. Uses `@mongo:27017` — the service name as hostname, resolved via Docker's internal DNS.

**`depends_on: - mongo`**

Same as `myapp` — starts after `mongo` container starts. In your terminal you saw mongo-express retrying the connection several times:

```
retrying to connect to mongo:27017 (2/10)
retrying to connect to mongo:27017 (3/10)
retrying to connect to mongo:27017 (4/10)
```

This is mongo-express's own built-in retry loop. It kept trying until MongoDB finished initializing, then connected successfully:

```
Mongo Express server listening at http://0.0.0.0:8081
```

This is different from `myapp` — mongo-express has retry logic built in, so `depends_on` being imprecise didn't cause a permanent failure.

---

### The shared network

Compose automatically creates a network named after the folder:

```
Network app_default   Created
```

All three services are attached to this network. The DNS rules:

- Inside `myapp`, `mongo` resolves to the IP of the `mongo` container.
- Inside `mongo-express`, `mongo` resolves to the same.
- From your Windows browser, neither `mongo` nor `myapp` is directly reachable by name — only through port mappings.

You never defined this network explicitly. Compose creates it for free whenever you have multiple services.

---

### Why name it `mongo.yaml` vs `docker-compose.yml`

If the file is named `docker-compose.yml` or `compose.yaml`, you can run:

```bash
docker compose up
```

Because those are the default filenames Compose looks for.

Since your file is named `mongo.yaml`, you must always specify it:

```bash
docker compose -f mongo.yaml up
```

Both approaches work. The `-f` flag lets you have multiple compose files for different purposes (e.g., `compose.dev.yaml`, `compose.prod.yaml`).

---

## 19. Development Workflow With Docker Compose

### The one command you use every day

```bash
cd /mnt/d/docker_practice/docker_compose2/app
docker compose -f mongo.yaml up
```

That is it. This is the normal workflow. You do not build manually. You do not pass `--build`. You just run `up`.

What Compose does when you run this:

- If the `myapp` image does not exist yet (first time ever), it builds it automatically from the Dockerfile.
- If the image already exists, it reuses it directly and starts all containers immediately.
- `mongo` and `mongo-express` are pulled from Docker Hub if not cached, then started.
- All three containers are attached to the shared network and start in dependency order.

From that point, your stack is running:

```
http://localhost:3000   → your Node app
http://localhost:8081   → mongo-express
```

### Stopping the stack

`Ctrl+C` in the terminal running Compose stops all containers gracefully.

### Stopping and removing containers

```bash
docker compose -f mongo.yaml down
```

Stops and removes the containers and the network. Images are kept. Data inside MongoDB is lost (no volumes defined in this project).

### Running in the background

```bash
docker compose -f mongo.yaml up -d
```

Starts everything detached — the terminal is free immediately. Containers keep running in the background until you explicitly stop them.

### Viewing logs when running detached

```bash
docker compose -f mongo.yaml logs
docker compose -f mongo.yaml logs myapp
docker compose -f mongo.yaml logs -f myapp
```

`-f` follows logs in real time (like `tail -f`).

### Checking what is running

```bash
docker ps
```

Shows all running containers with names, ports, and uptime.

---

### When `--build` is relevant (not the normal case)

`--build` forces Compose to rebuild the image even if it already exists. You only need this in one situation: you have changed your app code or Dockerfile and want the new version to be reflected in the container.

```bash
docker compose -f mongo.yaml up --build
```

This is not part of the everyday workflow. It is an explicit override for when you know the image is stale and needs to be recreated. In normal day-to-day use, you run `up` without it.

---

### Summary table

| Situation | Command |
|---|---|
| Normal start | `docker compose -f mongo.yaml up` |
| Start in background | `docker compose -f mongo.yaml up -d` |
| Stop | `Ctrl+C` |
| Stop and remove containers | `docker compose -f mongo.yaml down` |
| View logs | `docker compose -f mongo.yaml logs` |
| Follow live logs | `docker compose -f mongo.yaml logs -f` |
| Check running containers | `docker ps` |
| List images | `docker images` |
