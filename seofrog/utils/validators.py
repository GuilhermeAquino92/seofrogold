#!/usr/bin/env python3
"""
System validation utilities for SEOFrog
Validates system requirements and dependencies
"""
import sys
import importlib
from typing import List, Tuple
from seofrog.utils.logger import get_logger


def validate_system_requirements() -> bool:
    """
    Validate system requirements and dependencies
    
    Returns:
        bool: True if all requirements are met, False otherwise
    """
    logger = get_logger('Validator')
    
    try:
        # Check Python version
        if not _check_python_version():
            return False
            
        # Check required dependencies
        if not _check_dependencies():
            return False
            
        # Check system resources
        if not _check_system_resources():
            logger.warning("WARNING: System resources may be limited")
            
        logger.info("OK: System validation passed")
        return True
        
    except Exception as e:
        logger.error(f"ERROR: System validation failed: {e}")
        return False


def _check_python_version() -> bool:
    """Check if Python version meets requirements"""
    logger = get_logger('Validator')
    required_version = (3, 7)
    current_version = sys.version_info[:2]
    
    if current_version < required_version:
        logger.error(f"ERROR: Python {required_version[0]}.{required_version[1]}+ required. Current: {current_version[0]}.{current_version[1]}")
        return False
        
    logger.info(f"OK: Python version: {current_version[0]}.{current_version[1]}")
    return True


def _check_dependencies() -> bool:
    """Check if required dependencies are installed"""
    logger = get_logger('Validator')
    required_packages = [
        ('requests', 'HTTP client library'),
        ('pandas', 'Data analysis library'),
        ('aiohttp', 'Async HTTP client'),
        ('asyncio', 'Async I/O library'),
    ]
    
    missing_packages = []
    for package_name, description in required_packages:
        if not _is_package_installed(package_name):
            missing_packages.append((package_name, description))
    
    if missing_packages:
        logger.error("ERROR: Missing required dependencies:")
        for package, desc in missing_packages:
            logger.error(f" - {package}: {desc}")
        logger.error(" Install with: pip install " + " ".join([pkg[0] for pkg in missing_packages]))
        return False
        
    logger.info(f"OK: All {len(required_packages)} dependencies available")
    return True


def _is_package_installed(package_name: str) -> bool:
    """Check if a package is installed"""
    try:
        importlib.import_module(package_name.replace('-', '_'))
        return True
    except ImportError:
        return False


def _check_system_resources() -> bool:
    """Check system resources (memory, disk space)"""
    logger = get_logger('Validator')
    
    try:
        import psutil
        
        # Check available memory
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024**3)
        if available_gb < 1.0:
            logger.warning(f"WARNING: Low memory: {available_gb:.1f}GB available")
            return False
            
        # Check disk space
        disk = psutil.disk_usage('.')
        free_gb = disk.free / (1024**3)
        if free_gb < 1.0:
            logger.warning(f"WARNING: Low disk space: {free_gb:.1f}GB available")
            return False
            
        logger.info(f"OK: System resources: {available_gb:.1f}GB RAM, {free_gb:.1f}GB disk")
        return True
        
    except ImportError:
        logger.info("ℹ️ psutil not available - skipping resource check")
        return True
    except Exception as e:
        logger.warning(f"WARNING: Resource check failed: {e}")
        return True


def validate_url(url: str) -> Tuple[bool, str]:
    """
    Validate URL format and accessibility
    
    Args:
        url: URL to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not url:
        return False, "URL cannot be empty"
        
    if not url.startswith(('http://', 'https://')):
        return False, "URL must start with http:// or https://"
        
    # Basic URL format validation
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if not parsed.netloc:
            return False, "Invalid URL format - missing domain"
        return True, ""
    except Exception as e:
        return False, f"URL validation error: {e}"


def validate_output_directory(output_dir: str) -> Tuple[bool, str]:
    """
    Validate output directory
    
    Args:
        output_dir: Directory path to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    import os
    from pathlib import Path
    
    try:
        path = Path(output_dir)
        
        # Create directory if it doesn't exist
        path.mkdir(parents=True, exist_ok=True)
        
        # Check if writable
        test_file = path / '.write_test'
        try:
            test_file.touch()
            test_file.unlink()
        except Exception:
            return False, f"Directory is not writable: {output_dir}"
            
        return True, ""
        
    except Exception as e:
        return False, f"Directory validation error: {e}"