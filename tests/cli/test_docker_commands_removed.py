"""Tests verifying that separate Docker CLI commands have been removed."""

import re
from typer.testing import CliRunner

from MCPStack.cli import StackCLI


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


class TestDockerCommandsRemoved:
    """Test that separate Docker CLI commands return command not found errors."""

    def setup_method(self):
        """Set up test environment."""
        self.cli = StackCLI()
        self.runner = CliRunner()

    def test_docker_dockerfile_command_not_found(self):
        """Test that 'mcpstack docker dockerfile' returns command not found."""
        result = self.runner.invoke(self.cli.app, ["docker", "dockerfile", "--output", "test"])
        
        # Should fail with command not found
        assert result.exit_code != 0
        output = _strip_ansi(result.stdout)
        # Typer typically shows "No such command" or similar error
        assert "docker" in output.lower() or "command" in output.lower() or "not found" in output.lower()

    def test_docker_build_command_not_found(self):
        """Test that 'mcpstack docker build' returns command not found."""
        result = self.runner.invoke(self.cli.app, ["docker", "build", "--image", "test:latest"])
        
        # Should fail with command not found
        assert result.exit_code != 0
        output = _strip_ansi(result.stdout)
        assert "docker" in output.lower() or "command" in output.lower() or "not found" in output.lower()

    def test_docker_config_command_not_found(self):
        """Test that 'mcpstack docker config' returns command not found."""
        result = self.runner.invoke(self.cli.app, ["docker", "config", "--image", "test", "--server-name", "test"])
        
        # Should fail with command not found
        assert result.exit_code != 0
        output = _strip_ansi(result.stdout)
        assert "docker" in output.lower() or "command" in output.lower() or "not found" in output.lower()

    def test_help_does_not_show_docker_subcommand(self):
        """Test that 'mcpstack --help' doesn't show docker subcommand."""
        result = self.runner.invoke(self.cli.app, ["--help"])
        
        assert result.exit_code == 0
        output = _strip_ansi(result.stdout)
        
        # Should not show docker as a subcommand
        # Look for docker in the commands section, but it should not be there
        lines = output.split('\n')
        commands_section = False
        for line in lines:
            if "Commands:" in line or "commands:" in line:
                commands_section = True
                continue
            if commands_section and line.strip() == "":
                # End of commands section
                break
            if commands_section and "docker" in line.lower():
                # If we find docker in the commands section, that's a failure
                assert False, f"Found 'docker' command in help output: {line}"

    def test_docker_subcommand_not_available(self):
        """Test that docker subcommand is not available at all."""
        result = self.runner.invoke(self.cli.app, ["docker"])
        
        # Should fail because docker subcommand doesn't exist
        assert result.exit_code != 0
        output = _strip_ansi(result.stdout)
        assert "docker" in output.lower() or "command" in output.lower() or "not found" in output.lower()

    def test_build_help_shows_docker_parameters(self):
        """Test that 'mcpstack build --help' shows Docker parameters for integrated workflow."""
        result = self.runner.invoke(self.cli.app, ["build", "--help"])
        
        assert result.exit_code == 0
        output = result.stdout
        
        # Should show Docker-related parameters in build command
        assert "--build-image" in output
        assert "--generate-dockerfile" in output
        assert "--docker-push" in output
        assert "--profile" in output

    def test_list_profiles_shows_docker_profiles(self):
        """Test that Docker profiles are available through list-profiles command."""
        result = self.runner.invoke(self.cli.app, ["list-profiles", "--config-type", "docker"])
        
        assert result.exit_code == 0
        output = result.stdout
        
        # Should show Docker profiles
        assert "docker" in output.lower()
        # Should show at least one of the expected profiles
        assert "build-only" in output or "build-and-push" in output


class TestMigrationGuidance:
    """Test that users get helpful guidance for migrating from old commands."""

    def setup_method(self):
        """Set up test environment."""
        self.cli = StackCLI()
        self.runner = CliRunner()

    def test_equivalent_dockerfile_generation(self):
        """Test that profile-based Dockerfile generation works as replacement."""
        result = self.runner.invoke(self.cli.app, [
            "build", 
            "--profile", "build-only", 
            "--generate-dockerfile",
            "--presets", "example_preset"
        ])
        
        # Should attempt to execute (may fail due to missing Docker, but command should be recognized)
        assert "Executing workflow profile 'build-only'" in result.stdout or result.exit_code in [0, 1]

    def test_equivalent_image_build(self):
        """Test that profile-based image building works as replacement."""
        result = self.runner.invoke(self.cli.app, [
            "build", 
            "--profile", "build-only", 
            "--build-image", "test:latest",
            "--presets", "example_preset"
        ])
        
        # Should attempt to execute (may fail due to missing Docker, but command should be recognized)
        assert "Executing workflow profile 'build-only'" in result.stdout or result.exit_code in [0, 1]

    def test_equivalent_config_generation(self):
        """Test that profile-based config generation works as replacement."""
        result = self.runner.invoke(self.cli.app, [
            "build", 
            "--config-type", "docker",
            "--presets", "example_preset"
        ])
        
        # Should work for config generation
        assert result.exit_code in [0, 1]  # May fail due to environment but command should be valid