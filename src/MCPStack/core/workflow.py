"""Workflow profile management for MCPStack extended operations."""

import importlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ExecutionResult:
    """Result from executing a multi-stage workflow."""

    def __init__(self, results: Dict[str, Any]):
        self.results = results
        self.successful = all(not isinstance(result, Exception) for result in results.values())

    def get_stage_result(self, stage: str) -> Any:
        return self.results.get(stage)


class ProfileDefinition:
    """Definition of a workflow profile specifying stages and requirements."""

    def __init__(self, name: str, description: str, config_type: str, stages: List[str], requires: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self.config_type = config_type
        self.stages = stages
        self.requires = requires or []


class WorkflowRegistry:
    """Registry for managing workflow profiles and their definitions."""

    def __init__(self):
        self._profiles: Dict[str, ProfileDefinition] = {}
        self._load_builtin_profiles()
        self._discover_external_profiles()

    def _load_builtin_profiles(self) -> None:
        """Load built-in workflow profiles."""

        self._profiles["build-and-push"] = ProfileDefinition(
            name="build-and-push",
            description="Generate config, dockerfile, build image, and push",
            config_type="docker",
            stages=["config.generate", "dockerfile.generate", "image.build", "image.push"],
            requires=["docker_client", "registry_auth"]
        )

        self._profiles["build-only"] = ProfileDefinition(
            name="build-only",
            description="Generate config, dockerfile, and build image (local use)",
            config_type="docker",
            stages=["config.generate", "dockerfile.generate", "image.build"],
            requires=["docker_client"]
        )

        logger.debug(f"Loaded {len(self._profiles)} built-in workflow profiles")

    def _discover_external_profiles(self) -> None:
        """Discover external workflow profiles from configuration files."""
        try:

            workflows_dir = Path.cwd() / "workflows"
            if workflows_dir.exists():
                for yaml_file in workflows_dir.glob("*.yaml"):
                    try:
                        import yaml
                        with open(yaml_file) as f:
                            workflow_def = yaml.safe_load(f)

                        name = workflow_def.get("name", f"workflow-{yaml_file.stem}")
                        description = workflow_def.get("description", f"Custom workflow from {yaml_file.name}")
                        config_type = workflow_def.get("config_type")
                        stages = workflow_def.get("stages", [])
                        requires = workflow_def.get("requires", [])

                        if config_type and stages:
                            profile = ProfileDefinition(
                                name=name,
                                description=description,
                                config_type=config_type,
                                stages=stages,
                                requires=requires
                            )
                            self._profiles[name] = profile
                            logger.debug(f"Loaded external profile: {name}")
                    except Exception as e:
                        logger.warning(f"Failed to load workflow from {yaml_file}: {e}")
        except Exception as e:
            logger.debug(f"No external workflows directory found: {e}")

    def get_profile(self, name: str) -> Optional[ProfileDefinition]:
        """Get a workflow profile by name."""
        return self._profiles.get(name)

    def list_profiles(self) -> List[str]:
        """List all available workflow profile names."""
        return list(self._profiles.keys())

    def list_profiles_for_config_type(self, config_type: str) -> List[str]:
        """List workflow profiles available for a specific config type."""
        return [name for name, profile in self._profiles.items() if profile.config_type == config_type]


# Global registry instance
workflow_registry = WorkflowRegistry()


class ProfileOrchestrator:
    """Orchestrator for executing multi-stage workflow profiles."""

    def __init__(self):
        self.registry = workflow_registry

    def execute_workflow(self, profile_name: str, stack_context: Any, **kwargs) -> ExecutionResult:
        """Execute a full workflow profile."""
        profile = self.registry.get_profile(profile_name)
        if not profile:
            raise ValueError(f"Workflow profile '{profile_name}' not found")

        self._validate_requirements(profile)

        results = {}
        workflow_context = {}  # Track generated files and context between stages
        
        try:
            for stage_config in profile.stages:
                stage_name, stage_params = self._parse_stage_config(stage_config)

                merged_kwargs = {**kwargs, **workflow_context, **stage_params}
                
                if "." in stage_name:
                    component, operation = stage_name.split(".", 1)
                    result = self._execute_stage(component, operation, stack_context, stage_params, **merged_kwargs)
                else:
                    result = self._execute_builtin_stage(stage_name, stack_context, stage_params, **merged_kwargs)

                results[stage_name] = result

                if component == "dockerfile" and operation == "generate":

                    dockerfile_path = stage_params.get("path") or merged_kwargs.get("path", "Dockerfile")
                    workflow_context["dockerfile_path"] = dockerfile_path
                
                logger.info(f"Completed workflow stage: {stage_name}")

        except Exception as e:
            logger.error(f"Failed workflow stage '{stage_name}': {e}")
            results[stage_name] = e
            return ExecutionResult(results)

        return ExecutionResult(results)

    def _parse_stage_config(self, stage_config) -> tuple[str, dict]:
        """Parse stage configuration, supporting both string and dict formats.
        
        Args:
            stage_config: Either a string like "dockerfile.generate" or a dict like
                         {"dockerfile.generate": {"path": "Dockerfile.prod", "base": "python:3.11-alpine"}}
        
        Returns:
            Tuple of (stage_name, parameters_dict)
        """
        if isinstance(stage_config, str):
            return stage_config, {}
        elif isinstance(stage_config, dict):
            if len(stage_config) != 1:
                raise ValueError(f"Stage config dict must have exactly one key: {stage_config}")
            stage_name = list(stage_config.keys())[0]
            stage_params = stage_config[stage_name]
            return stage_name, stage_params
        else:
            raise ValueError(f"Invalid stage config type: {type(stage_config)}")

    def _validate_requirements(self, profile: ProfileDefinition) -> None:
        """Validate that all requirements for a profile are satisfied."""
        for requirement in profile.requires:
            if requirement == "docker_client":
                if not self._check_docker_available():
                    raise RuntimeError("Docker client is required but not available")
            elif requirement == "registry_auth":
                if not self._check_registry_auth():
                    raise RuntimeError("Docker registry authentication is required")


    def _check_docker_available(self) -> bool:
        """Check if Docker is available on the system."""
        try:
            import subprocess
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False

    def _check_registry_auth(self) -> bool:
        """Check if Docker registry is configured."""

        return self._check_docker_available()

    def _execute_stage(self, component: str, operation: str, stack_context: Any, stage_params: dict, **kwargs) -> Any:
        """Execute a specific workflow stage."""

        merged_kwargs = {**kwargs, **stage_params}
        
        if component == "config":
            return self._execute_config_stage(operation, stack_context, **merged_kwargs)
        elif component == "dockerfile":
            return self._execute_dockerfile_stage(operation, stack_context, **merged_kwargs)
        elif component == "image":
            return self._execute_image_stage(operation, stack_context, **merged_kwargs)
        else:
            raise ValueError(f"Unknown workflow component: {component}")

    def _execute_config_stage(self, operation: str, stack_context: Any, **kwargs) -> Any:
        """Execute configuration-related stage."""
        if operation == "generate":
            build_kwargs = {
                "type": kwargs.get("config_type", "fastmcp"),
                "command": kwargs.get("command"),
                "args": kwargs.get("args"),
                "cwd": kwargs.get("cwd"),
                "module_name": kwargs.get("module_name"),
                "pipeline_config_path": kwargs.get("pipeline_config_path"),
                "save_path": kwargs.get("save_path"),
                "build_image": kwargs.get("build_image"),
                "generate_dockerfile": kwargs.get("generate_dockerfile"),
                "dockerfile_path": kwargs.get("dockerfile_path"),
                "docker_push": kwargs.get("docker_push"),
                "docker_registry_url": kwargs.get("docker_registry_url"),
                "build_args": kwargs.get("build_args"),
            }

            build_kwargs = {k: v for k, v in build_kwargs.items() if v is not None}

            result = stack_context.build(**build_kwargs)

            pipeline_config_path = kwargs.get("pipeline_config_path", "mcpstack_pipeline.json")
            if pipeline_config_path:
                stack_context.save(pipeline_config_path)

            return result
        else:
            raise ValueError(f"Unknown config operation: {operation}")

    def _execute_dockerfile_stage(self, operation: str, stack_context: Any, **kwargs) -> Any:
        """Execute dockerfile-related stage."""
        from MCPStack.core.docker.dockerfile_generator import DockerfileGenerator

        if operation == "generate":

            dockerfile_path = kwargs.get("path") or kwargs.get("dockerfile_path") or "Dockerfile"
            base_image = kwargs.get("base") or kwargs.get("base_image", "python:3.13-slim")
            package_name = kwargs.get("package", "mcpstack")
            local_package_path = kwargs.get("local_package_path")

            import os
            if local_package_path is None and os.path.exists("src/MCPStack") and os.path.exists("pyproject.toml"):

                local_package_path = "."
                package_name = None  # Don't install from PyPI when using local source

            return DockerfileGenerator.save(
                stack=stack_context,
                path=Path(dockerfile_path),
                base_image=base_image,
                package_name=package_name,
                local_package_path=local_package_path
            )
        else:
            raise ValueError(f"Unknown dockerfile operation: {operation}")

    def _execute_image_stage(self, operation: str, stack_context: Any, **kwargs) -> Any:
        """Execute image-related stage."""
        from MCPStack.core.docker.docker_builder import DockerBuilder
        import os
        import string

        image_name = kwargs.get("image_name") or kwargs.get("image", "mcpstack:latest")
        build_args = kwargs.get("build_args", {})
        dockerfile_path = kwargs.get("dockerfile_path") or kwargs.get("path", "Dockerfile")

        template_vars = {
            **os.environ,
            'preset': kwargs.get('presets', 'mcpstack').split(',')[0] if kwargs.get('presets') else 'mcpstack'
        }
        
        try:
            image_name = string.Template(image_name).safe_substitute(template_vars)
        except (KeyError, ValueError) as e:
            logger.warning(f"Failed to expand variables in image name '{image_name}': {e}")

        if operation == "build":
            return DockerBuilder.build(
                dockerfile_path=Path(dockerfile_path),
                image_name=image_name,
                build_args=build_args
            )
        elif operation == "push":
            registry_url = kwargs.get("registry_url") or kwargs.get("registry")
            return DockerBuilder.push(
                image_name=image_name,
                registry_url=registry_url
            )
        else:
            raise ValueError(f"Unknown image operation: {operation}")

    def _execute_builtin_stage(self, stage: str, stack_context: Any, stage_params: dict, **kwargs) -> Any:
        """Execute a built-in workflow stage."""

        merged_kwargs = {**kwargs, **stage_params}
        raise ValueError(f"Built-in stage '{stage}' not implemented")


