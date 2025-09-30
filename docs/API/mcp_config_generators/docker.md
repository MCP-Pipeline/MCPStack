# DockerMCP Config Generator

::: MCPStack.core.mcp_config_generator.mcp_config_generators.docker_mcp_config.DockerMCPConfigGenerator
    options:
      show_root_heading: true
      show_source: true

## Docker Workflow

The DockerMCP Config Generator provides unified Docker containerization functionality for MCPStack pipelines. It can:

- **Generate configuration files** for running MCPStack tools inside Docker containers (Claude Desktop integration)
- **Generate Dockerfiles** from MCPStack pipeline configurations
- **Build Docker images** automatically during configuration generation
- **Push images** to Docker registries
- **Support complex configuration** including volumes, ports, networks, and build arguments

## Usage

### Basic Configuration Generation
```python
config = DockerMCPConfigGenerator.generate(
    stack=mcp_stack,
    image_name="mcpstack:myapp"
)
```

### Complete Docker Workflow
```python
config = DockerMCPConfigGenerator.generate(
    stack=mcp_stack,
    image_name="myapp:latest",
    build_image="myapp:latest",  # Build the image
    generate_dockerfile=True,    # Generate Dockerfile
    docker_push=True,           # Push to registry
    docker_registry_url="docker.io/username/"
)
```

## CLI Integration

The generator integrates with the unified MCPStack CLI through workflow profiles:

```bash
# Generate Docker config only (basic usage)
mcpstack build --config-type docker --presets my_preset

# Generate config, dockerfile, build and push (production pipeline)
mcpstack build --config-type docker --presets my_preset --profile build-and-push

# Generate config, dockerfile, and build locally (development)
mcpstack build --config-type docker --presets my_preset --profile build-only
```

## Parameters

### Core Parameters
- `stack`: MCPStackCore instance
- `image_name`: Docker image name to use in configurations
- `server_name`: Name for the MCP server in Claude config
- `volumes`: Volume mounts for Docker container
- `ports`: Port mappings for Docker container
- `network`: Docker network name

### Docker Building Parameters
- `build_image`: Image name to build (triggers Docker build)
- `generate_dockerfile`: Generate Dockerfile when True
- `dockerfile_path`: Custom path for generated Dockerfile
- `docker_push`: Push built image to registry
- `docker_registry_url`: Docker registry URL
- `build_args`: Dictionary of Docker build arguments

## Integration with MCP Config Generators Registry

The DockerMCP Config Generator is automatically available through the MCP config generators registry:

```python
from MCPStack.core.mcp_config_generator.registry import ALL_MCP_CONFIG_GENERATORS

# The DockerMCP generator is registered as 'docker'
generator = ALL_MCP_CONFIG_GENERATORS['docker']
config = generator.generate(stack, build_image="myimage:latest")
