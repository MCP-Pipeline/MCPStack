"""Tests for ProfileManager functionality."""

import pytest
from unittest.mock import Mock, patch
from MCPStack.core.profile_manager import ProfileManager, ProfileInfo, ValidationResult
from MCPStack.core.workflow import ProfileDefinition


class TestProfileManager:
    """Test cases for ProfileManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.profile_manager = ProfileManager()

    def test_list_profiles_all(self):
        """Test listing all profiles."""
        profiles = self.profile_manager.list_profiles()
        
        assert len(profiles) >= 2  # At least build-only and build-and-push
        profile_names = [p.name for p in profiles]
        assert "build-only" in profile_names
        assert "build-and-push" in profile_names

    def test_list_profiles_filtered_by_config_type(self):
        """Test listing profiles filtered by config type."""
        docker_profiles = self.profile_manager.list_profiles(config_type="docker")
        
        assert len(docker_profiles) >= 2
        for profile in docker_profiles:
            assert profile.config_type == "docker"

    def test_validate_profile_existing(self):
        """Test validating an existing profile."""
        result = self.profile_manager.validate_profile("build-only")
        
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_profile_nonexistent(self):
        """Test validating a non-existent profile."""
        result = self.profile_manager.validate_profile("nonexistent-profile")
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert "not found" in result.errors[0]

    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_docker_available')
    def test_validate_profile_missing_docker(self, mock_docker_check):
        """Test validation when Docker is not available."""
        mock_docker_check.return_value = False
        
        result = self.profile_manager.validate_profile("build-only")
        
        assert len(result.missing_requirements) > 0
        assert any("Docker client" in req for req in result.missing_requirements)

    def test_suggest_profiles_exact_match(self):
        """Test profile suggestions with exact match."""
        suggestions = self.profile_manager.suggest_profiles("build-only")
        
        assert "build-only" in suggestions

    def test_suggest_profiles_fuzzy_match(self):
        """Test profile suggestions with fuzzy matching."""
        suggestions = self.profile_manager.suggest_profiles("build")
        
        assert len(suggestions) > 0
        assert any("build" in suggestion for suggestion in suggestions)

    def test_suggest_profiles_no_match(self):
        """Test profile suggestions with no good matches."""
        suggestions = self.profile_manager.suggest_profiles("xyz123nonexistent")
        
        # Should return empty list or very low-confidence matches
        assert len(suggestions) <= 1

    def test_get_profile_info_existing(self):
        """Test getting info for an existing profile."""
        info = self.profile_manager.get_profile_info("build-only")
        
        assert info is not None
        assert info.name == "build-only"
        assert info.config_type == "docker"
        assert info.source == "built-in"
        assert len(info.stages) > 0

    def test_get_profile_info_nonexistent(self):
        """Test getting info for a non-existent profile."""
        info = self.profile_manager.get_profile_info("nonexistent")
        
        assert info is None

    @patch('MCPStack.core.workflow.ProfileOrchestrator.execute_workflow')
    def test_execute_profile_success(self, mock_execute):
        """Test successful profile execution."""
        mock_stack = Mock()
        mock_result = Mock()
        mock_execute.return_value = mock_result
        
        result = self.profile_manager.execute_profile("build-only", mock_stack)
        
        assert result == mock_result
        mock_execute.assert_called_once()

    def test_execute_profile_invalid(self):
        """Test executing an invalid profile."""
        mock_stack = Mock()
        
        with pytest.raises(ValueError, match="Profile validation failed"):
            self.profile_manager.execute_profile("nonexistent", mock_stack)

    @patch('MCPStack.core.workflow.ProfileOrchestrator.execute_workflow')
    def test_execute_profile_execution_error(self, mock_execute):
        """Test profile execution with runtime error."""
        mock_stack = Mock()
        mock_execute.side_effect = RuntimeError("Execution failed")
        
        with pytest.raises(RuntimeError, match="Execution failed"):
            self.profile_manager.execute_profile("build-only", mock_stack)


class TestProfileInfo:
    """Test cases for ProfileInfo data class."""

    def test_profile_info_creation(self):
        """Test creating ProfileInfo instance."""
        info = ProfileInfo(
            name="test-profile",
            description="Test profile",
            config_type="docker",
            stages=["config.generate"],
            requires=["docker_client"],
            source="built-in"
        )
        
        assert info.name == "test-profile"
        assert info.is_valid is True
        assert info.validation_errors == []

    def test_profile_info_with_errors(self):
        """Test ProfileInfo with validation errors."""
        info = ProfileInfo(
            name="invalid-profile",
            description="Invalid profile",
            config_type="docker",
            stages=[],
            requires=[],
            source="external",
            is_valid=False,
            validation_errors=["No stages defined"]
        )
        
        assert info.is_valid is False
        assert len(info.validation_errors) == 1


class TestValidationResult:
    """Test cases for ValidationResult data class."""

    def test_validation_result_valid(self):
        """Test creating valid ValidationResult."""
        result = ValidationResult(is_valid=True)
        
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.missing_requirements == []

    def test_validation_result_invalid(self):
        """Test creating invalid ValidationResult with errors."""
        result = ValidationResult(
            is_valid=False,
            errors=["Profile not found"],
            warnings=["Docker not available"],
            missing_requirements=["docker_client"]
        )
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert len(result.warnings) == 1
        assert len(result.missing_requirements) == 1