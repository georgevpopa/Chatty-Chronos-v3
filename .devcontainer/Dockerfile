FROM mcr.microsoft.com/devcontainers/python:3.11

# Install any additional system dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI so we can interact with host Docker daemon inside the devcontainer
RUN curl -fsSL https://get.docker.com -o get-docker.sh && \
    sh get-docker.sh && \
    usermod -aG docker vscode

# The user is 'vscode' (provided by the base image)
