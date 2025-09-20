"""Profile management system for MCPStack workflow orchestration."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from thefuzz import process

from .workflow import ProfileDefinition, ProfileOrchestrator, WorkflowRegistry, ExecutionResult, workflow_registry

logger = logging.getLogger(__name__)


@dataclass
class ProfileInfo:
    """Information about a workflow profile."""
    name: str
    description: str
    config_type: str
    stages: List[Union[str, Dict[str, Any]]]
    requires: List[str]
    source: str  # "built-in" or file path
    is_valid: bool = True
    validation_errors: List[str] = None

    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []


@dataclass
class ValidationResult:
    """Result of profile validation."""
    is_valid: bool
    errors: List[str] = None
    warnings: List[str] = None
    missing_requirements: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.missing_requirements is None:
            self.missing_requirements = []


class ProfileManager:
    """Manages profile discovery, validation, and execution coordination."""

    def __init__(self):
        self.registry = workflow_registry
        self.orchestrator = ProfileOrchestrator()

    def list_profiles(self, config_type: Optional[str] = None) -> List[ProfileInfo]:
        """List available workflow profiles with detailed information.
        
        Args:
            config_type: Optional filter by config type (e.g., 'docker')
            
        Returns:
            List of ProfileInfo objects with profile details
        """
        profiles = []
        
        if config_type:
            profile_names = self.registry.list_profiles_for_config_type(config_type)
        else:
            profile_names = self.registry.list_profiles()
        
        for name in profile_names:
            profile_def = self.registry.get_profile(name)
            if profile_def:
                # Determine source (built-in vs external)
                source = "built-in" if name in ["build-only", "build-and-push"] else "external"
                
                profile_info = ProfileInfo(
                    name=profile_def.name,
                    description=profile_def.description,
                    config_type=profile_def.config_type,
                    stages=profile_def.stages,
                    requires=profile_def.requires,
                    source=source
                )
                profiles.append(profile_info)
        
        return profiles

    def validate_profile(self, profile_name: str) -> ValidationResult:
        """Validate a profile and its requirements.
        
        Args:
            profile_name: Name of the profile to validate
            
        Returns:
            ValidationResult with validation status and any errors
        """
        result = ValidationResult(is_valid=True)
        
        # Check if profile exists
        profile = self.registry.get_profile(profile_name)
        if not profile:
            result.is_valid = False
            result.errors.append(f"Profile '{profile_name}' not found")
            return result
        
        # Validate requirements
        missing_reqs = []
        for requirement in profile.requires:
            if requirement == "docker_client":
                if not self.orchestrator._check_docker_available():
                    missing_reqs.append("Docker client (install Docker Desktop or Docker Engine)")
            elif requirement == "registry_auth":
                if not self.orchestrator._check_registry_auth():
                    missing_reqs.append("Docker registry authentication (run 'docker login')")
        
        if missing_reqs:
            result.missing_requirements = missing_reqs
            result.warnings.append("Some requirements are not met but profile can still be validated")
        
        # Validate stages
        for stage in profile.stages:
            try:
                stage_name, stage_params = self.orchestrator._parse_stage_config(stage)
                # Basic validation of stage format
                if "." in stage_name:
                    component, operation = stage_name.split(".", 1)
                    if component not in ["config", "dockerfile", "image"]:
                        result.warnings.append(f"Unknown component '{component}' in stage '{stage_name}'")
            except Exception as e:
                result.errors.append(f"Invalid stage configuration: {e}")
                result.is_valid = False
        
        return result

    def execute_profile(self, profile_name: str, stack_context: Any, **kwargs) -> ExecutionResult:
        """Execute a workflow profile.
        
        Args:
            profile_name: Name of the profile to execute
            stack_context: MCPStack context for execution
            **kwargs: Additional parameters for profile execution
            
        Returns:
            ExecutionResult with execution status and results
        """
        # Validate profile first
        validation = self.validate_profile(profile_name)
        if not validation.is_valid:
            raise ValueError(f"Profile validation failed: {'; '.join(validation.errors)}")
        
        # Warn about missing requirements but allow execution
        if validation.missing_requirements:
            logger.warning(f"Missing requirements for profile '{profile_name}': {', '.join(validation.missing_requirements)}")
        
        # Execute the workflow
        try:
            return self.orchestrator.execute_workflow(profile_name, stack_context, **kwargs)
        except Exception as e:
            logger.error(f"Profile execution failed: {e}")
            raise

    def suggest_profiles(self, query: str, limit: int = 3) -> List[str]:
        """Suggest profile names based on fuzzy matching.
        
        Args:
            query: Query string to match against
            limit: Maximum number of suggestions to return
            
        Returns:
            List of suggested profile names
        """
        available_profiles = self.registry.list_profiles()
        if not available_profiles:
            return []
        
        # Use fuzzy matching to find similar profiles
        matches = process.extract(query, available_profiles, limit=limit)
        return [match[0] for match in matches if match[1] > 60]  # Only return matches with >60% similarity

    def get_profile_info(self, name: str) -> Optional[ProfileInfo]:
        """Get detailed information about a specific profile.
        
        Args:
            name: Profile name
            
        Returns:
            ProfileInfo object or None if profile not found
        """
        profile_def = self.registry.get_profile(name)
        if not profile_def:
            return None
        
        # Determine source
        source = "built-in" if name in ["build-only", "build-and-push"] else "external"
        
        # Validate the profile
        validation = self.validate_profile(name)
        
        return ProfileInfo(
            name=profile_def.name,
            description=profile_def.description,
            config_type=profile_def.config_type,
            stages=profile_def.stages,
            requires=profile_def.requires,
            source=source,
            is_valid=validation.is_valid,
            validation_errors=validation.errors
        )