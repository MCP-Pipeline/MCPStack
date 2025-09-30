# MCPStack Workflow Profiles

This directory contains example workflow profile definitions that extend MCPStack's basic configuration generation with multi-stage operations.

## What are Workflow Profiles?

Workflow profiles define sequences of operations that go beyond basic config generation. They allow you to orchestrate complex deployment pipelines while maintaining MCPStack's clean architecture.

## Built-in Profiles

MCPStack ships with these built-in profiles:

- `build-and-push`: Generate config, dockerfile, build image, push to registry
- `build-only`: Generate config, dockerfile, and build image locally

Use built-in profiles with:
```bash
mcpstack build --presets your-preset --config-type docker --profile build-and-push
```

List available profiles:
```bash
mcpstack list-profiles                    # All profiles
mcpstack list-profiles --config-type docker  # Docker-only profiles
```

## Custom Profiles

Create your own profiles by adding YAML files to this directory. Each profile defines:

```yaml
name: my-custom-profile          # Profile identifier
description: "What this profile does"  # Shown in listings
config_type: docker              # Must match your --config-type

stages:                          # Operations to execute in order
  - config.generate              # Always first stage
  - dockerfile.generate          # May specify custom path
  - image.build                  # Build Docker image
  - image.push                   # Push to registry

requires:                        # Pre-execution validation
  - docker_client                # Required dependencies
  - registry_auth
```

## Stage Reference

### config.generate
Generates MCP configuration (required first stage)
```yaml
# No additional configuration needed
- config.generate
```

### dockerfile.generate
Generates Dockerfile from your stack configuration
```yaml
- dockerfile.generate:
    path: Dockerfile.custom  # Custom dockerfile path (optional)
```

### image.build
Builds Docker image using generated dockerfile
```yaml
- image.build:
    image: "myapp:latest"          # Image name:tag
    build_args:                    # Docker build arguments (optional)
      BUILDKIT_INLINE_CACHE: 1
      ENVIRONMENT: production
```

### image.push
Pushes built image to registry
```yaml
- image.push:
    image: "myapp:latest"          # Image to push
    registry: "docker.io"          # Registry URL (optional)
    tags: ["latest", "v1.0.0"]     # Additional tags (optional)
```

## Environment Variables

Profiles support environment variable substitution using `${VARIABLE}` syntax:

- `${preset}` - The preset name passed to `--presets`
- `${GIT_COMMIT}` - Current git commit hash
- `${GIT_BRANCH}` - Current git branch name
- Any environment variable: `${MY_VAR}`

## Requirements Check

Profiles can specify requirements that are validated before execution:

- `docker_client`: Docker daemon must be available
- `registry_auth`: Registry authentication configured
- `git_available`: Git repository with commit info
- Custom requirements can be added to the validation logic

## Examples

See the included example profiles:
- `docker-dev.yaml` - Development workflow (build locally)
- `docker-prod.yaml` - Production workflow (build, tag, push)

Copy these files and customize them for your needs. MCPStack automatically discovers profiles in this directory.
