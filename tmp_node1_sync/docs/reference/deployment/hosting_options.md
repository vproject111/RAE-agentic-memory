# Hosting Options for RAE Agentic Memory

RAE Agentic Memory is designed to be flexible, supporting both local-first development and cloud-first deployments. This document outlines various hosting options and considerations.

## 1. Local-First Deployment (Docker Compose)

For local development and testing, the easiest way to run RAE is using Docker Compose. This sets up all necessary services (Postgres, Qdrant, Memory API, Reranker Service) on your local machine.

*   **Setup**: Refer to the [Getting Started](getting_started.md) guide for detailed instructions on how to use `docker compose up`.
*   **Benefits**: Simple setup, isolated environment, no cloud costs during development.
*   **Use Case**: Local development, testing, small-scale personal projects.

## 2. Cloud-First Deployment

For production environments, scalability, and reliability, deploying RAE to the cloud is recommended. This typically involves using managed services for the database and vector store, and containerized deployments for the API services.

### 2.1 Managed Databases

Instead of running your own Postgres and Qdrant instances, you can leverage managed cloud services.

*   **PostgreSQL**:
    *   **Supabase**: A popular open-source Firebase alternative that provides managed Postgres.
        *   **Configuration**: Update `POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` in your `memory-api` configuration to point to your Supabase instance.
    *   **AWS RDS / Google Cloud SQL / Azure Database for PostgreSQL**: Enterprise-grade managed PostgreSQL services.
        *   **Configuration**: Similar to Supabase, update Postgres connection details.

*   **Qdrant**:
    *   **Qdrant Cloud**: The official managed service for Qdrant.
        *   **Configuration**: Update `QDRANT_HOST` and `QDRANT_PORT` (or use `QDRANT_URL` if provided by Qdrant Cloud) in your `memory-api` configuration. You might also need an API key for Qdrant Cloud.

### 2.2 Serverless Deployment of API Services

The `memory-api` and `reranker-service` are FastAPI applications, which can be easily containerized and deployed to serverless platforms.

*   **Containerization**: Both services are already containerized using Dockerfiles.
*   **Platforms**:
    *   **Google Cloud Run**: A fully managed compute platform for deploying containerized applications.
        *   **Deployment Steps**:
            1.  Build and push your Docker images to Google Container Registry (GCR) or Artifact Registry.
            2.  Deploy the images to Cloud Run, configuring environment variables for database connections and RAE API Key.
            3.  Ensure proper IAM roles for database access.
    *   **AWS Fargate (ECS)**: A serverless compute engine for Amazon ECS that allows you to run containers without managing servers or clusters.
        *   **Deployment Steps**:
            1.  Build and push your Docker images to Amazon ECR.
            2.  Define ECS tasks and services using Fargate launch type.
            3.  Configure environment variables and IAM roles.
    *   **AWS Lambda with Container Images**: Deploy your FastAPI application as a container image to AWS Lambda.
        *   **Deployment Steps**:
            1.  Build and push your Docker images to Amazon ECR.
            2.  Create a Lambda function, selecting "Container image" as the package type.
            3.  Configure environment variables and API Gateway for HTTP access.

### 2.3 Considerations for Serverless

*   **Cold Starts**: Serverless functions can experience cold starts, which might introduce latency for the first request after a period of inactivity.
*   **Database Connections**: Manage database connection pooling carefully. `asyncpg` is well-suited for this.
*   **Environment Variables**: All sensitive configurations (API keys, database credentials) should be passed securely via environment variables.
*   **Cost**: Serverless platforms are cost-effective for variable workloads, as you only pay for compute time used.

## Conclusion

Choosing the right hosting option depends on your project's scale, budget, and operational requirements. RAE's modular design and containerization make it adaptable to a wide range of deployment scenarios, from local development to scalable cloud-native applications.
