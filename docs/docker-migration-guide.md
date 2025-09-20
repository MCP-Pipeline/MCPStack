# Docker Commands Migration Guide

## Overview

As part of MCPStack's architectural improvements, the separate Docker CLI commands have been removed to eliminate workflow fragmentation. All Docker functionality is now integrated into the main `mcpstack build` command using profiles.

## Migration Summary

The separate `mcpstack docker` subcommands have been **removed** and replaced with an integrated workflow approach using profiles. This provides a more consistent user experience and eliminates the need to learn multiple separate commands.

## Command Migration Table

| **Removed Command** | **New Integrated Command** | **Notes** |
|---------------------|----------------------------|-----------|
| `mcpstack docker dockerfile --output Dockerfile` | `mcpstack build --profile build-only --generate-dockerfile --dockerfile-path Dockerfile` | Use build-only profile with dockerfile generation |
| `mcpstack docker build --image my-app:latest` | `mcpstack build --profile build-only --build-image my-app:latest` | Use build-only profile with image building |
| `mcpstack docker config --image my-app --server-name test` | `mcpstack build --config-type docker --output config.json` | Use docker config type directly |

## Common Migration Scenarios

### Scenario 1: Generate Dockerfile Only

**Before (Removed):**
```bash
mcpstack docker dockerfile --presets example_preset --output Dockerfile
```

**After (New Approach):**
```bash
mcpstack build --profile build-only --presets example_preset --generate-dockerfile --dockerfile-path Dockerfile
```

### Scenario 2: Build Docker Image

**Before (Removed):**
```bash
mcpstack docker build --presets example_preset --image myapp:latest
```

**After (New Approach):**
```bash
mcpstack build --profile build-only --presets example_preset --build-image myapp:latest
```

### Scenario 3: Generate Docker MCP Configuration

**Before (Removed):**
```bash
mcpstack docker config --presets example_preset --output config.json
```

**After (New Approach):**
```bash
mcpstack build --config-type docker --presets example_preset --output config.json
```

### Scenario 4: Complete Docker Workflow (Build + Push)

**Before (Multiple Commands):**
```bash
mcpstack docker dockerfile --presets example_preset --output Dockerfile
mcpstack docker build --presets example_preset --image myapp:latest
# Manual docker push myapp:latest
```

**After (Single Command):**
```bash
mcpstack build --profile build-and-push --presets example_preset --build-image myapp:latest
```

## Available Docker Profiles

The integrated approach provides several built-in profiles for common Docker workflows:

### `build-only` Profile
- **Purpose**: Local development and testing
- **Stages**: Config generation → Dockerfile generation → Image building
- **Usage**: `mcpstack build --profile build-only --presets example_preset`

### `build-and-push` Profile  
- **Purpose**: Complete deployment workflow
- **Stages**: Config generation → Dockerfile generation → Image building → Registry push
- **Usage**: `mcpstack build --profile build-and-push --presets example_preset --build-image myapp:latest`

## Docker Parameters Reference

All Docker-related parameters are now available directly in the `mcpstack build` command:

| **Parameter** | **Description** | **Example** |
|---------------|-----------------|-------------|
| `--profile` | Workflow profile to execute | `--profile build-only` |
| `--build-image` | Docker image name to build | `--build-image myapp:latest` |
| `--generate-dockerfile` | Generate Dockerfile | `--generate-dockerfile` |
| `--dockerfile-path` | Custom Dockerfile path | `--dockerfile-path ./custom/Dockerfile` |
| `--docker-push` | Push image to registry | `--docker-push` |
| `--docker-registry-url` | Registry URL for pushing | `--docker-registry-url registry.example.com` |
| `--build-args` | Docker build arguments | `--build-args "ENV=prod,VERSION=1.0"` |

## Troubleshooting

### Error: Command 'docker' not found

If you see this error when trying to run old Docker commands:

```bash
$ mcpstack docker dockerfile
Error: No such command 'docker'
```

**Solution**: Use the integrated approach with profiles:
```bash
mcpstack build --profile build-only --generate-dockerfile
```

### Missing Docker Parameters

If you're missing Docker-specific functionality:

1. **Check available profiles**: `mcpstack list-profiles --config-type docker`
2. **Use docker config type**: `--config-type docker` 
3. **Review parameters**: `mcpstack build --help`

### Profile Not Found

If you get a "Profile not found" error:

```bash
$ mcpstack build --profile my-profile
Error: Profile 'my-profile' not found. Did you mean: build-only, build-and-push?
```

**Solution**: Use one of the available Docker profiles or create a custom profile in the `workflows/` directory.

## Benefits of the New Approach

1. **Unified Workflow**: All MCPStack functionality uses the same `build` command pattern
2. **Fewer Commands**: Learn one command instead of multiple Docker subcommands  
3. **Profile Flexibility**: Easily switch between different Docker workflows
4. **Better Integration**: Docker parameters work seamlessly with other MCPStack features
5. **Extensibility**: Create custom profiles for specific deployment needs

## Quick Reference Card

For quick reference, here are the most common migration patterns:

```bash
# OLD: mcpstack docker dockerfile
# NEW: mcpstack build --profile build-only --generate-dockerfile

# OLD: mcpstack docker build --image myapp:latest  
# NEW: mcpstack build --profile build-only --build-image myapp:latest

# OLD: mcpstack docker config
# NEW: mcpstack build --config-type docker
```

## Getting Help

- **List available profiles**: `mcpstack list-profiles --config-type docker`
- **View build command help**: `mcpstack build --help`
- **View all commands**: `mcpstack --help`

For additional support, refer to the main MCPStack documentation or the Docker Architecture Guide.