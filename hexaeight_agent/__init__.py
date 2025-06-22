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

__version__ = "1.6.8"
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
from .hexaeight_agent import enable_library_debug, is_library_debug_enabled

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
    
    # Availability flags
    "DOTNET_AVAILABLE",
    "HEXAEIGHT_AGENT_AVAILABLE",
]
