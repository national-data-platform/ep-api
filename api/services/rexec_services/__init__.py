"""
High-level entry points for Rexec service orchestration.
"""

from .create_rexec_server_resources import create_rexec_server_resources

# Only expose the create_rexec_server_resources function
__all__ = ["create_rexec_server_resources"]
