"""Docker build utilities for MCPStack."""
import logging
import subprocess
from pathlib import Path

from beartype import beartype
from beartype.typing import Any, Dict, List, Optional

from MCPStack.core.utils.exceptions import MCPStackValidationError

logger = logging.getLogger(__name__)


@beartype
class DockerBuilder:
    """Utilities for building Docker images from MCPStack configurations."""

    @classmethod
    def build(
        cls,
        dockerfile_path: Path,
        image_name: str,
        context_path: Optional[str] = None,
        build_args: Optional[Dict[str, str]] = None,
        no_cache: bool = False,
        quiet: bool = False,
    ) -> Dict[str, Any]:
        """Build a Docker image from a Dockerfile.

        Args:
            dockerfile_path: Path to the Dockerfile
            image_name: Name and tag for the built image
            context_path: Build context path (defaults to dockerfile directory)
            build_args: Build arguments to pass to Docker
            no_cache: Disable Docker build cache
            quiet: Suppress build output

        Returns:
            Dict with build result information

        Raises:
            MCPStackValidationError: If build fails
        """
        if not dockerfile_path.exists():
            raise MCPStackValidationError(f"Dockerfile not found: {dockerfile_path}")
        
        # Default context to dockerfile directory
        if context_path is None:
            context_path = str(dockerfile_path.parent)
        
        # Build Docker command
        cmd = [
            "docker", "build",
            "-t", image_name,
            "-f", str(dockerfile_path),
        ]
        
        # Add build arguments
        if build_args:
            for key, value in build_args.items():
                cmd.extend(["--build-arg", f"{key}={value}"])
        
        # Add flags
        if no_cache:
            cmd.append("--no-cache")
        
        if quiet:
            cmd.append("--quiet")
        
        # Add context path as final argument
        cmd.append(context_path)
        
        logger.info(f"Building Docker image: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            
            logger.info(f"✅ Successfully built Docker image: {image_name}")
            
            return {
                "success": True,
                "image_name": image_name,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Docker build failed: {e}")
            logger.error(f"stdout: {e.stdout}")
            logger.error(f"stderr: {e.stderr}")
            
            raise MCPStackValidationError(
                f"Docker build failed with exit code {e.returncode}: {e.stderr}"
            )
        
        except FileNotFoundError:
            raise MCPStackValidationError(
                "Docker command not found. Please ensure Docker is installed and in PATH."
            )

    @classmethod
    def push(
        cls,
        image_name: str,
        registry_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Push a Docker image to a registry.

        Args:
            image_name: Name and tag of the image to push
            registry_url: Optional registry URL (if not included in image name)

        Returns:
            Dict with push result information

        Raises:
            MCPStackValidationError: If push fails
        """
        # Construct full image name with registry if provided
        full_image_name = image_name
        if registry_url:
            if not image_name.startswith(registry_url):
                full_image_name = f"{registry_url.rstrip('/')}/{image_name}"
        
        cmd = ["docker", "push", full_image_name]
        
        logger.info(f"Pushing Docker image: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            
            logger.info(f"✅ Successfully pushed Docker image: {full_image_name}")
            
            return {
                "success": True,
                "image_name": full_image_name,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Docker push failed: {e}")
            raise MCPStackValidationError(
                f"Docker push failed with exit code {e.returncode}: {e.stderr}"
            )
        
        except FileNotFoundError:
            raise MCPStackValidationError(
                "Docker command not found. Please ensure Docker is installed and in PATH."
            )

    @classmethod
    def tag(
        cls,
        source_image: str,
        target_image: str,
    ) -> Dict[str, Any]:
        """Tag a Docker image with a new name.

        Args:
            source_image: Source image name and tag
            target_image: Target image name and tag

        Returns:
            Dict with tag result information

        Raises:
            MCPStackValidationError: If tagging fails
        """
        cmd = ["docker", "tag", source_image, target_image]
        
        logger.info(f"Tagging Docker image: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            
            logger.info(f"✅ Successfully tagged image: {source_image} -> {target_image}")
            
            return {
                "success": True,
                "source_image": source_image,
                "target_image": target_image,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Docker tag failed: {e}")
            raise MCPStackValidationError(
                f"Docker tag failed with exit code {e.returncode}: {e.stderr}"
            )
        
        except FileNotFoundError:
            raise MCPStackValidationError(
                "Docker command not found. Please ensure Docker is installed and in PATH."
            )

    @classmethod
    def list_images(cls, filter_name: Optional[str] = None) -> List[Dict[str, str]]:
        """List available Docker images.

        Args:
            filter_name: Optional filter to match image names

        Returns:
            List of image information dictionaries

        Raises:
            MCPStackValidationError: If listing fails
        """
        cmd = ["docker", "images", "--format", "json"]
        
        if filter_name:
            cmd.extend(["--filter", f"reference={filter_name}"])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            
            images = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    import json
                    try:
                        image_info = json.loads(line)
                        images.append(image_info)
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse Docker image info: {line}")
            
            return images
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Docker images command failed: {e}")
            raise MCPStackValidationError(
                f"Failed to list Docker images: {e.stderr}"
            )
        
        except FileNotFoundError:
            raise MCPStackValidationError(
                "Docker command not found. Please ensure Docker is installed and in PATH."
            )