"""Additional tests for Docker config generator to reach 95% coverage."""
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from MCPStack.core.config import StackConfig
from MCPStack.core.docker.docker_config_generator import DockerConfigGenerator
from MCPStack.core.utils.exceptions import MCPStackValidationError
from MCPStack.stack import MCPStackCore


class TestDockerConfigGeneratorCoverage:
    """Additional tests for Docker config generator to improve coverage."""

    def test_save_without_claude_config_path(self):
        """Test save when Claude config path cannot be found."""
        config = StackConfig()
        stack = MCPStackCore(config)
        
        with patch.object(DockerConfigGenerator, '_get_claude_config_path', return_value=None):
            # Should not raise error, just log warning
            DockerConfigGenerator.save(
                stack=stack,
                image_name="test:latest"
            )

    def test_merge_with_existing_config_io_error(self):
        """Test merge config with IO error during read."""
        config = StackConfig()
        stack = MCPStackCore(config)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text("invalid json content")
            
            # Should handle JSON decode error gracefully
            DockerConfigGenerator._merge_with_existing_config(
                {"mcpServers": {"test": {}}},
                config_path
            )
            
            # Should still write the new config
            with open(config_path) as f:
                result = json.load(f)
            assert "test" in result["mcpServers"]

    def test_merge_with_existing_config_write_error(self):
        """Test merge config with write permission error."""
        config = StackConfig()
        stack = MCPStackCore(config)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "readonly.json"
            config_path.write_text('{"mcpServers": {}}')
            config_path.chmod(0o444)  # Read-only
            
            try:
                with pytest.raises(MCPStackValidationError, match="Could not write config file"):
                    DockerConfigGenerator._merge_with_existing_config(
                        {"mcpServers": {"test": {}}},
                        config_path
                    )
            finally:
                # Restore write permissions for cleanup
                config_path.chmod(0o644)

    def test_generate_with_empty_volumes_and_ports(self):
        """Test generate with empty volumes and ports lists."""
        config = StackConfig()
        stack = MCPStackCore(config)
        
        docker_config = DockerConfigGenerator.generate(
            stack=stack,
            image_name="test:latest",
            volumes=[],
            ports=[]
        )
        
        # Should not add volume or port arguments
        args = docker_config["mcpServers"]["mcpstack"]["args"]
        assert "-v" not in args
        assert "-p" not in args

    def test_save_with_existing_config_file(self):
        """Test save merging with existing config file."""
        config = StackConfig()
        stack = MCPStackCore(config)
        
        existing_config = {
            "mcpServers": {
                "existing": {
                    "command": "python",
                    "args": ["-m", "existing"],
                    "env": {}
                }
            }
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            with open(config_path, "w") as f:
                json.dump(existing_config, f)
            
            with patch.object(DockerConfigGenerator, '_get_claude_config_path', return_value=config_path):
                DockerConfigGenerator.save(
                    stack=stack,
                    image_name="test:latest",
                    server_name="new_server"
                )
            
            # Check merged config
            with open(config_path) as f:
                merged = json.load(f)
            
            assert "existing" in merged["mcpServers"]
            assert "new_server" in merged["mcpServers"]
            assert merged["mcpServers"]["new_server"]["args"][-1] == "test:latest"