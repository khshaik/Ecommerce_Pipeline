# Setup & Installation Guide

## System Requirements

### Hardware
- **CPU**: 2+ cores (4+ recommended)
- **RAM**: 8GB minimum (16GB recommended)
- **Disk**: 10GB free space
- **OS**: macOS, Linux, or Windows (with WSL2)

### Software
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Python**: 3.8+ (for local script execution)
- **Git**: For version control

## Installation Steps

### 1. Install Docker & Docker Compose

#### macOS (using Homebrew)
```bash
brew install docker docker-compose
# Or use Docker Desktop: https://www.docker.com/products/docker-desktop
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install docker.io docker-compose
sudo usermod -aG docker $USER
```

#### Windows
Download Docker Desktop from: https://www.docker.com/products/docker-desktop

### 2. Verify Installation

```bash
docker --version
docker-compose --version
python3 --version
```

Expected output:
```
Docker version 20.10.x, build xxxxxxx
Docker Compose version 2.x.x, build xxxxxxx
Python 3.8.x
```

### 3. Clone/Navigate to Project

```bash
cd /path/to/2025em1100102
```

### 4. Build Docker Image

```bash
docker-compose build
```

This creates the custom Spark image with:
- Apache Spark 3.4.0
- Python dependencies (pyyaml, pandas, psycopg2, kafka-python)
- PostgreSQL JDBC driver

**Build time**: 5-10 minutes (first time)

### 5. Start Services

```bash
docker-compose up -d
```

**Startup time**: 30-60 seconds

### 6. Verify All Services Running

```bash
docker-compose ps
```

Expected output:
```
NAME                COMMAND                  SERVICE             STATUS
spark-master        /opt/spark/bin/spark-... spark-master        Up 2 minutes
spark-worker-a      /opt/spark/bin/spark-... spark-worker-a      Up 2 minutes
spark-worker-b      /opt/spark/bin/spark-... spark-worker-b      Up 2 minutes
postgres            docker-entrypoint.s...   postgres            Up 2 minutes
kafka               /etc/confluent/docker... kafka               Up 2 minutes
zookeeper           /etc/confluent/docker... zookeeper           Up 2 minutes
spark-runner        tail -f /dev/null        spark-runner        Up 2 minutes
```

### 7. Test Connectivity

```bash
# Test PostgreSQL
docker-compose exec spark-runner python3 scripts/test_postgres_connection.py

# Test Kafka
docker-compose exec spark-runner python3 scripts/test_kafka_producer.py
```

## Port Mappings

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| Spark Master UI | 9090 | http://localhost:9090 | Monitor Spark jobs |
| Spark Worker A UI | 9091 | http://localhost:9091 | Monitor worker A |
| Spark Worker B UI | 9785 | http://localhost:9785 | Monitor worker B |
| PostgreSQL | 5432 | localhost:5432 | Database connection |
| Kafka Broker | 29095 | localhost:29095 | Kafka producer/consumer |
| Zookeeper | 2888 | localhost:2888 | Kafka coordination |

## Volume Mappings

| Host Path | Container Path | Purpose |
|-----------|-----------------|---------|
| `./postgres_data` | `/var/lib/postgresql/data` | PostgreSQL data persistence |
| `./db` | `/docker-entrypoint-initdb.d` | SQL initialization scripts |
| `./datalake` | `/app/datalake` | Data lake output |
| `.` | `/app` | Project root |

## Environment Variables

### PostgreSQL
```
POSTGRES_USER=student
POSTGRES_PASSWORD=student123
POSTGRES_DB=food_delivery_db
```

### Kafka
```
KAFKA_BROKER_ID=1
KAFKA_ZOOKEEPER_CONNECT=zookeeper:2888
KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:9095,PLAINTEXT_HOST://0.0.0.0:29095
KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9095,PLAINTEXT_HOST://localhost:29095
```

### Spark
```
SPARK_DRIVER_MEMORY=1G
SPARK_EXECUTOR_MEMORY=1G
SPARK_WORKER_CORES=1
SPARK_WORKER_MEMORY=1G
```

## Configuration Files

### docker-compose.yml
Defines all services and their configurations. Key sections:
- `spark-master`: Spark cluster master
- `spark-worker-a/b`: Spark cluster workers
- `spark-runner`: Container for running Spark jobs
- `postgres`: PostgreSQL database
- `kafka`: Kafka broker
- `zookeeper`: Kafka coordination

### Dockerfile
Custom Spark image with:
- Base: `apache/spark-py:v3.4.0`
- Python packages: pyyaml, pandas, psycopg2-binary, kafka-python
- PostgreSQL JDBC driver (v42.7.3)

### configs/orders_stream.yml
Central configuration for pipeline:
- PostgreSQL connection details
- Kafka broker and topic configuration
- Streaming parameters
- Data validation rules
- Data lake paths

## Troubleshooting Installation

### Docker daemon not running
```bash
# macOS
open /Applications/Docker.app

# Linux
sudo systemctl start docker
```

### Permission denied errors
```bash
# Linux: Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Port already in use
```bash
# Find process using port
lsof -i :9090

# Kill process
kill -9 <PID>

# Or change port in docker-compose.yml
```

### Out of disk space
```bash
# Clean up Docker
docker system prune -a

# Remove volumes
docker volume prune
```

### Container fails to start
```bash
# Check logs
docker-compose logs <service-name>

# Rebuild image
docker-compose build --no-cache

# Restart services
docker-compose down
docker-compose up -d
```

## Next Steps

1. Read `README.md` for project overview
2. Review `configs/orders_stream.yml` for configuration
3. Follow the Quick Start Guide in README.md
4. Run verification scripts
5. Start producer and consumer

## Getting Help

If you encounter issues:

1. Check logs: `docker-compose logs -f <service>`
2. Run verification: `docker-compose exec spark-runner python3 scripts/verify_pipeline.py --config configs/orders_stream.yml`
3. Check port availability: `netstat -an | grep LISTEN`
4. Review troubleshooting section in README.md
