# StackCLI

!!! note "Scope"
    This page documents the **programmatic** CLI class — handy if you embed the CLI or generate help programmatically.
    For end-user command help, see the **CLI** section of the docs.

## Workflow Profiles

The `build` command supports workflow profiles for executing multi-stage operations beyond basic config generation:

- `--profile NAME`: Run extended workflow profile after basic build

### Profile Discovery

```bash
# List all available profiles
mcpstack list-profiles

# List profiles for specific config type
mcpstack list-profiles --config-type docker
```

### Profile Examples

```bash
# Generate Docker config only (basic usage)
mcpstack build --config-type docker --presets example_preset

# Execute build-and-push workflow profile
mcpstack build --config-type docker --presets example_preset --profile build-and-push

# Execute build-only workflow profile
mcpstack build --config-type docker --presets example_preset --profile build-only
```

### Built-in Docker Profiles

- `build-and-push`: Generate config, dockerfile, build image, push to registry
- `build-only`: Generate config, dockerfile, build image locally

### Custom Profiles

Create YAML profiles in the `workflows/` directory for complex deployment scenarios:

```yaml
name: docker-prod
description: Production deployment with tagging
config_type: docker
stages:
  - config.generate
  - dockerfile.generate
  - image.build:
      image: "${preset}:${GIT_COMMIT}"
  - image.push:
      registry: "docker.io"
      tags: ["latest", "${GIT_BRANCH}"]
```

::: MCPStack.cli.StackCLI
    options:
      show_root_heading: true
      show_source: true
