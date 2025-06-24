"""
HexaEight Agent - Python Library for AI Agent Coordination

A comprehensive Python library for HexaEight identity management, PubSub messaging,
task coordination, and multi-agent collaboration.

Key Features:
- Full PubSub messaging capabilities
- Task creation and management
- Message locking and scheduling
- LLM gateway integration
- Real-time event handling
- Parent and Child agent support

Example Usage:
    # Basic agent setup
    from hexaeight_agent import HexaEightAgent, HexaEightEnvironmentManager
    
    # Load environment
    HexaEightEnvironmentManager.load_hexaeight_variables_from_env_file("env-file")
    
    # Create and configure agent
    async with HexaEightAgent() as agent:
        agent.load_ai_parent_agent("parent_config.json")
        await agent.connect_to_pubsub("http://pubsub-server:5000")
        
        # Send message
        await agent.publish_broadcast("http://pubsub-server:5000", "Hello world!")
        
        # Handle events
        async for event_type, event_data in agent.events():
            if event_type == 'message_received':
                print(f"Message: {event_data.decrypted_content}")
            elif event_type == 'scheduled_task_creation':
                print(f"Scheduled task: {event_data.title}")

Requirements:
    - .NET 8.0+ runtime
    - Access to HexaEight PubSub server
    - HexaEight credentials and configuration
"""

import os
import platform
import shutil
from pathlib import Path

def _setup_native_libraries():
    """
    Copy the appropriate native SQLite.Interop.dll based on the current OS and architecture.
    This ensures SQLite native interop works correctly across different platforms.
    """
    try:
        # Get the package directory
        package_dir = Path(__file__).parent
        dlls_dir = package_dir / "dlls"
        
        if not dlls_dir.exists():
            print("⚠️ HexaEight Agent: DLLs directory not found, skipping native library setup")
            return
        
        # Detect OS and architecture
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        # Map to the correct subfolder
        native_lib_map = {
            ("windows", "amd64"): "win-x64",
            ("windows", "x86_64"): "win-x64", 
            ("windows", "x86"): "win-x86",
            ("windows", "i386"): "win-x86",
            ("linux", "x86_64"): "linux-x64",
            ("linux", "amd64"): "linux-x64",
            ("darwin", "x86_64"): "osx-x64",
            ("darwin", "arm64"): "osx-x64",  # Use x64 version for Apple Silicon via Rosetta
        }
        
        # Find the correct subfolder
        subfolder = None
        for (os_name, arch), folder in native_lib_map.items():
            if system == os_name and (machine == arch or 
                                    (arch == "amd64" and machine == "x86_64") or 
                                    (arch == "x86_64" and machine == "amd64")):
                subfolder = folder
                break
        
        if not subfolder:
            print(f"⚠️ HexaEight Agent: No native SQLite library found for {system}-{machine}")
            print(f"Available options: {list(set(native_lib_map.values()))}")
            return
        
        # Source and destination paths
        source_dir = dlls_dir / subfolder
        source_file = source_dir / "SQLite.Interop.dll"
        dest_file = dlls_dir / "SQLite.Interop.dll"
        
        # Check if source exists
        if not source_file.exists():
            print(f"⚠️ HexaEight Agent: Native SQLite library not found: {source_file}")
            return
        
        # Copy if destination doesn't exist or is different
        should_copy = True
        if dest_file.exists():
            # Check if files are the same size (simple check)
            if source_file.stat().st_size == dest_file.stat().st_size:
                should_copy = False
        
        if should_copy:
            shutil.copy2(source_file, dest_file)
            print(f"✅ HexaEight Agent: Configured native SQLite library for {system}-{machine}")
        # Only show success message in verbose mode to avoid spam
        elif os.environ.get('HEXAEIGHT_VERBOSE'):
            print(f"✅ HexaEight Agent: Native SQLite library ready for {system}-{machine}")
            
    except Exception as e:
        print(f"⚠️ HexaEight Agent: Failed to setup native libraries: {e}")
        print("SQLite operations may not work properly")

# Setup native libraries on import - this happens automatically when package is imported
_setup_native_libraries()

__version__ = "1.6.805"
__author__ = "HexaEight"
__license__ = "Apache 2.0"

# Import main classes and functions
from .hexaeight_agent import (
    # Main agent class
    HexaEightAgent,
    HexaEightAgentConfig,  # Alias for backwards compatibility
    
    # Environment management
    HexaEightEnvironmentManager,
    
    # Data classes
    TaskStep,
    TaskInfo,
    MessageLock,
    LLMMessage,
    LLMRequest,
    LLMResponse,
    
    # Event classes
    MessageReceivedEvent,
    TaskReceivedEvent,
    TaskStepEvent,
    TaskStepUpdateEvent,
    TaskCompleteEvent,
    ScheduledTaskCreationEvent,  # Added missing scheduled task event
    
    # Enums
    MessageType,
    TargetType,
    
    # Exceptions
    HexaEightAgentError,
    
    # Legacy compatibility (deprecated)
    HexaEightMessage,
    HexaEightJWT,
    HexaEightConfig,
    HexaEightConfiguration,
)

# Import global debug control functions
from .hexaeight_agent import enable_library_debug, is_library_debug_enabled, show_examples, get_demo_path, get_create_scripts_path

# Expose availability flags
from .hexaeight_agent import DOTNET_AVAILABLE, HEXAEIGHT_AGENT_AVAILABLE

__all__ = [
    # Main classes
    "HexaEightAgent",
    "HexaEightAgentConfig",
    "HexaEightEnvironmentManager",
    
    # Data classes
    "TaskStep",
    "TaskInfo", 
    "MessageLock",
    "LLMMessage",
    "LLMRequest",
    "LLMResponse",
    
    # Event classes
    "MessageReceivedEvent",
    "TaskReceivedEvent",
    "TaskStepEvent",
    "TaskStepUpdateEvent",
    "TaskCompleteEvent",
    "ScheduledTaskCreationEvent",  # Added missing scheduled task event
    
    # Enums
    "MessageType",
    "TargetType",
    
    # Exceptions
    "HexaEightAgentError",
    
    # Legacy (deprecated)
    "HexaEightMessage",
    "HexaEightJWT", 
    "HexaEightConfig",
    "HexaEightConfiguration",
    
    # Global debug control
    "enable_library_debug",
    "is_library_debug_enabled",
    "show_examples",
    "get_demo_path",
    "get_create_scripts_path",
    
    # Availability flags
    "DOTNET_AVAILABLE",
    "HEXAEIGHT_AGENT_AVAILABLE",
]
