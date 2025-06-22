"""
HexaEight Identity Python Library - Clean Message Handover

Rewritten to provide clean handover like Agent.cs - passes raw content to demo handlers
without pre-processing interference.
"""

import os
import json
import sys
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Tuple, List, Optional, Any, AsyncGenerator, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import threading
import queue
import weakref

# Flag to track whether .NET components are available
DOTNET_AVAILABLE = False
HEXAEIGHT_AGENT_AVAILABLE = False

# Global debug flag for library-level debugging (separate from agent-level)
LIBRARY_DEBUG = False

def _library_debug_log(message: str):
    """Library-level debug logging."""
    if LIBRARY_DEBUG:
        print(f"🔧 LIB DEBUG: {message}")

# Try to initialize Python.NET and load .NET components
try:
    import pythonnet
    from pythonnet import load
    
    # Load the .NET Core runtime
    _library_debug_log("Loading .NET Core runtime...")
    load("coreclr")
    _library_debug_log("✅ .NET Core runtime loaded")
    
    import clr
    _library_debug_log(f"CLR module loaded: {type(clr)}")
    
    # Verify CLR bridge is working
    if not hasattr(clr, 'AddReference'):
        raise ImportError("CLR bridge failed - AddReference method not available")
    
    _library_debug_log("✅ CLR bridge established successfully")
    
    # Add the HexaEightAgent assembly to the path
    def add_assemblies():
        """Load the HexaEightAgent assembly from the bundled dlls directory."""
        dll_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dlls")
        
        if not os.path.exists(dll_dir):
            raise FileNotFoundError(f"HexaEight DLL directory not found: {dll_dir}")
        
        sys.path.append(dll_dir)
        _library_debug_log(f"Added DLL directory to path: {dll_dir}")
        
        # Load assemblies in dependency order
        try:
            clr.AddReference("HexaEightAgent")
            _library_debug_log("✅ HexaEightAgent assembly loaded")
            
            # Load other assemblies
            assemblies = ["Newtonsoft.Json", "SystemHelper", "System.Text.Json", 
                         "jose-jwt", "HexaEightJWTLibrary", "HexaEightASKClientLibrary"]
            for assembly in assemblies:
                try:
                    clr.AddReference(assembly)
                    _library_debug_log(f"✅ Loaded assembly: {assembly}")
                except Exception as e:
                    _library_debug_log(f"⚠️ Assembly failed: {assembly} ({e})")
                    
        except Exception as e:
            raise ImportError(f"Failed to load HexaEightAgent assembly: {e}")

    add_assemblies()
    
    # Import C# classes - only import what actually exists
    _library_debug_log("Importing HexaEight classes...")
    from HexaEightAgent import Message as CSharpMessage
    from HexaEightAgent import AgentConfig as CSharpAgentConfig
    from HexaEightAgent import EnvironmentManager as CSharpEnvironmentManager
    
    # Try to import event args - these may not exist in all versions
    try:
        from HexaEightAgent import EnhancedPubSubSubscriptionEventArgs
        _library_debug_log("✅ EnhancedPubSubSubscriptionEventArgs imported")
    except ImportError:
        _library_debug_log("⚠️ EnhancedPubSubSubscriptionEventArgs not available")
        # Create a dummy class
        class EnhancedPubSubSubscriptionEventArgs:
            def __init__(self):
                self.Topic = ""
                self.Sender = ""
                self.SenderInternalId = ""
                self.DecryptedContent = ""
                self.Timestamp = None
                self.MessageId = ""
                self.IsTaskMessage = False
                self.IsFromSelf = False
                self.IsScheduleNotification = False
                self.IsLockExpired = False
    
    # Import System types
    from System import DateTime, Environment, String, Guid
    from System.Threading.Tasks import Task
    from System.Collections.Generic import List as CSharpList
    
    DOTNET_AVAILABLE = True
    HEXAEIGHT_AGENT_AVAILABLE = True
    _library_debug_log("✅ Successfully imported all HexaEightAgent classes")
    
except Exception as e:
    print(f"CRITICAL ERROR: Failed to initialize Python.NET or load HexaEightAgent assembly:")
    print(f"Error: {e}")
    print("\nHexaEightAgent .NET assembly is REQUIRED for this library to function.")
    print("Please ensure:")
    print("1. .NET 8.0+ runtime is installed")
    print("2. pythonnet is properly installed: 'pip install pythonnet>=3.0.0'")
    print("3. HexaEightAgent.dll is present in the dlls/ directory")
    import traceback
    traceback.print_exc()


class HexaEightAgentError(Exception):
    """Exception raised when HexaEightAgent functionality is not available."""
    pass


def _ensure_agent_available():
    """Ensure HexaEightAgent is available, raise exception if not."""
    if not HEXAEIGHT_AGENT_AVAILABLE:
        raise HexaEightAgentError(
            "HexaEightAgent .NET assembly is not available. "
            "Please ensure the HexaEightAgent NuGet package DLL is installed "
            "in the dlls/ directory and .NET runtime is available."
        )


# ==================================================================================
# SIMPLE MESSAGE CLASS - NO PRE-PROCESSING
# ==================================================================================

class HexaEightMessage:
    """Simple message wrapper - provides raw access without interference."""
    
    def __init__(self, debug_mode: bool = False):
        _ensure_agent_available()
        self._clr_message = CSharpMessage()
        self.debug_mode = debug_mode
    
    def _debug_log(self, message: str):
        """Debug logging for message operations."""
        if self.debug_mode:
            print(f"🔍 MSG DEBUG: {message}")
    
    @property
    def request(self): return self._clr_message.REQUEST
    @request.setter
    def request(self, value): self._clr_message.REQUEST = value
    
    @property
    def sender(self): return self._clr_message.SENDER
    @sender.setter  
    def sender(self, value): self._clr_message.SENDER = value
    
    @property
    def receiver(self): return self._clr_message.RECEIVER
    @receiver.setter
    def receiver(self, value): self._clr_message.RECEIVER = value
    
    @property
    def body(self): return self._clr_message.BODY
    @body.setter
    def body(self, value): self._clr_message.BODY = value
    
    def parse_body(self): 
        """Parse the message body."""
        self._debug_log("Parsing message body")
        self._clr_message.ParseBody()
    
    # Basic getter methods - no processing
    def get_content(self) -> str:
        """Get parsed content from the message body."""
        content = self._clr_message.GetContent() or ""
        self._debug_log(f"Getting content: {content[:50]}...")
        return content
    
    def get_raw_body(self) -> str:
        """Get raw content from BODY field."""
        body = self._clr_message.GetRawBody() or ""
        self._debug_log(f"Getting raw body: {body[:50]}...")
        return body
    
    def get_content_or_body(self) -> str:
        """Get content with fallback to body if content is empty."""
        content = self._clr_message.GetContentOrBody() or ""
        self._debug_log(f"Getting content or body: {content[:50]}...")
        return content
    
    def get_sender(self) -> str:
        """Get sender information."""
        return self._clr_message.GetSender() or ""
    
    def get_receiver(self) -> str:
        """Get receiver information."""
        return self._clr_message.GetReceiver() or ""
    
    def get_request(self) -> str:
        """Get request type/information."""
        return self._clr_message.GetRequest() or ""
    
    def get_user_scope(self) -> str:
        """Get user scope from parsed message."""
        return self._clr_message.GetUserScope() or ""
    
    def get_program_hash(self) -> str:
        """Get program hash from parsed message."""
        return self._clr_message.GetProgramHash() or ""
    
    def get_code_challenge(self) -> str:
        """Get code challenge from parsed message."""
        return self._clr_message.GetCodeChallenge() or ""
    
    def get_sender_time(self) -> datetime:
        """Get sender time as UTC DateTime."""
        try:
            dt = self._clr_message.GetSenderTime()
            return datetime(dt.Year, dt.Month, dt.Day, dt.Hour, dt.Minute, dt.Second, dt.Microsecond)
        except Exception as e:
            self._debug_log(f"Error getting sender time: {e}")
            return datetime.utcnow()
    
    def get_receiver_time(self) -> datetime:
        """Get receiver time as UTC DateTime."""
        try:
            dt = self._clr_message.GetReceiverTime()
            return datetime(dt.Year, dt.Month, dt.Day, dt.Hour, dt.Minute, dt.Second, dt.Microsecond)
        except Exception as e:
            self._debug_log(f"Error getting receiver time: {e}")
            return datetime.utcnow()
    
    def get_transmission_time_seconds(self) -> float:
        """Get transmission time in seconds."""
        return self._clr_message.GetTransmissionTimeSeconds()
    
    def get_transmission_time_milliseconds(self) -> float:
        """Get transmission time in milliseconds."""
        return self._clr_message.GetTransmissionTimeMilliseconds()
    
    def has_parsed_data(self) -> bool:
        """Check if message has been parsed successfully."""
        return self._clr_message.HasParsedData()
    
    def has_content(self) -> bool:
        """Check if message has content."""
        return self._clr_message.HasContent()
    
    def get_content_as_json(self) -> Optional[Dict[str, Any]]:
        """Attempt to parse content as JSON."""
        try:
            json_dict = self._clr_message.GetContentAsJson()
            if json_dict is None:
                return None
            
            # Convert C# dictionary to Python dictionary
            result = {}
            for key in json_dict.Keys:
                value = json_dict[key]
                # Handle different value types
                if hasattr(value, 'ToString'):
                    result[str(key)] = str(value)
                else:
                    result[str(key)] = value
            return result
        except Exception as e:
            self._debug_log(f"Error parsing content as JSON: {e}")
            return None
    
    def get_all_properties(self) -> Dict[str, Any]:
        """Get dictionary of all parsed properties."""
        try:
            props_dict = self._clr_message.GetAllProperties()
            result = {}
            
            for key in props_dict.Keys:
                value = props_dict[key]
                
                # Convert C# types to Python types
                if hasattr(value, 'ToDateTime'):
                    # DateTime conversion
                    dt = value.ToDateTime()
                    result[str(key)] = datetime(dt.Year, dt.Month, dt.Day, dt.Hour, dt.Minute, dt.Second, dt.Microsecond)
                elif hasattr(value, 'ToString'):
                    result[str(key)] = str(value)
                else:
                    result[str(key)] = value
                    
            return result
        except Exception as e:
            self._debug_log(f"Error getting all properties: {e}")
            return {}
    
    def get_summary(self) -> str:
        """Get summary of the message for debugging."""
        return self._clr_message.GetSummary() or ""
    
    def to_json(self) -> str:
        """Convert message to formatted JSON."""
        return self._clr_message.ToJson() or "{}"
    
    def to_compact_json(self) -> str:
        """Convert message to compact JSON."""
        return self._clr_message.ToCompactJson() or "{}"
    
    @classmethod
    def parse(cls, json_string: str, debug_mode: bool = False):
        """Parse message from JSON string."""
        try:
            clr_message = CSharpMessage.Parse(json_string)
            message = cls.__new__(cls)
            message._clr_message = clr_message
            message.debug_mode = debug_mode
            return message
        except Exception as e:
            if debug_mode:
                print(f"🔍 MSG DEBUG: Error parsing message: {e}")
            return None
    
    def __str__(self): 
        return self.get_summary()


# ==================================================================================
# DATA CLASSES FOR PYTHON REPRESENTATION
# ==================================================================================

@dataclass
class TaskStep:
    """Represents a task step."""
    step_number: int
    description: str
    completed: bool = False
    completed_by: str = ""
    completed_at: Optional[datetime] = None


@dataclass
class TaskInfo:
    """Represents task information."""
    task_id: str
    title: str
    description: str
    steps: List[TaskStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
    created_by_internal_id: str = ""


@dataclass
class MessageLock:
    """Represents a message lock."""
    message_id: str
    locked_by: str
    locked_by_internal_id: str
    locked_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(minutes=1))


@dataclass
class LLMMessage:
    """Represents an LLM message."""
    role: str
    content: str


@dataclass
class LLMRequest:
    """Represents an LLM request."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    provider: str = "openai"
    model: str = ""
    messages: List[LLMMessage] = field(default_factory=list)
    max_tokens: int = 1000
    temperature: float = 0.7
    requester_internal_id: str = ""


@dataclass
class LLMResponse:
    """Represents an LLM response."""
    request_id: str
    original_request_message_id: str
    success: bool
    content: str = ""
    error_message: str = ""
    tokens_used: int = 0
    cost: float = 0.0
    provider: str = ""
    model: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


class MessageType(Enum):
    """Message types."""
    MESSAGE = "message"
    TASK = "task"
    TASK_RESPONSE = "task_response"
    SCHEDULED_TASK = "scheduled_task"


class TargetType(Enum):
    """Target types for message routing."""
    DIRECT = "direct"
    BROADCAST = "broadcast"
    AGENT_NAME = "agent_name"
    GROUP = "group"


# ==================================================================================
# EVENT HANDLING - CLEAN HANDOVER
# ==================================================================================

@dataclass
class MessageReceivedEvent:
    """Event data for received messages - RAW content handover."""
    topic: str
    sender: str
    sender_internal_id: str
    decrypted_content: str  # RAW decrypted content - no pre-processing
    timestamp: datetime
    message_id: str
    is_task_message: bool = False
    is_from_self: bool = False
    is_schedule_notification: bool = False
    is_lock_expired: bool = False


@dataclass
class TaskReceivedEvent:
    """Event data for received tasks."""
    task_id: str
    title: str
    description: str
    total_steps: int
    status: str
    created_by: str
    created_at: datetime
    message_id: str


@dataclass
class TaskStepEvent:
    """Event data for task steps."""
    parent_task_id: str
    step_number: int
    description: str
    status: str
    message_id: str
    sender: str = ""


@dataclass
class TaskStepUpdateEvent:
    """Event data for task step updates."""
    parent_task_id: str
    step_number: int
    status: str
    completed_by: str
    completed_at: datetime
    result: Any = None


@dataclass
class TaskCompleteEvent:
    """Event data for task completion."""
    task_id: str
    completed_by: str
    completed_at: datetime


@dataclass
class ScheduledTaskCreationEvent:
    """Event data for scheduled task creation - clean processed data from C#."""
    task_id: str
    title: str
    description: str
    steps: List[str]
    scheduled_by: str
    scheduled_by_internal_id: str
    original_schedule_time: datetime


# ==================================================================================
# ENVIRONMENT MANAGER (KEEP AS-IS)
# ==================================================================================

class HexaEightEnvironmentManager:
    """Python wrapper for HexaEightAgent.EnvironmentManager."""
    
    RESOURCENAME_KEY = "HEXAEIGHT_RESOURCENAME"
    RESOURCENAME_KEY2 = "HEXA8_RESOURCENAME"
    MACHINETOKEN_KEY = "HEXAEIGHT_MACHINETOKEN"
    SECRET_KEY = "HEXAEIGHT_SECRET"
    LICENSECODE_KEY = "HEXAEIGHT_LICENSECODE"
    
    @staticmethod
    def get_all_environment_variables():
        """Get all HexaEight environment variables."""
        _ensure_agent_available()
        try:
            result_tuple = CSharpEnvironmentManager.GetAllEnvironmentVariables()
            resource_name = getattr(result_tuple, 'Item1', None) or ""
            machine_token = getattr(result_tuple, 'Item2', None) or ""
            secret = getattr(result_tuple, 'Item3', None) or ""
            license_code = getattr(result_tuple, 'Item4', None) or ""
            
            # Sync with Python environment if .NET is empty
            if not resource_name and not machine_token:
                py_resource = os.environ.get(HexaEightEnvironmentManager.RESOURCENAME_KEY)
                py_token = os.environ.get(HexaEightEnvironmentManager.MACHINETOKEN_KEY)
                py_secret = os.environ.get(HexaEightEnvironmentManager.SECRET_KEY)
                py_license = os.environ.get(HexaEightEnvironmentManager.LICENSECODE_KEY)
                
                if py_resource or py_token:
                    if DOTNET_AVAILABLE:
                        try:
                            if py_resource:
                                Environment.SetEnvironmentVariable(HexaEightEnvironmentManager.RESOURCENAME_KEY, py_resource)
                                Environment.SetEnvironmentVariable(HexaEightEnvironmentManager.RESOURCENAME_KEY2, py_resource)
                            if py_token:
                                Environment.SetEnvironmentVariable(HexaEightEnvironmentManager.MACHINETOKEN_KEY, py_token)
                            if py_secret:
                                Environment.SetEnvironmentVariable(HexaEightEnvironmentManager.SECRET_KEY, py_secret)
                            if py_license:
                                Environment.SetEnvironmentVariable(HexaEightEnvironmentManager.LICENSECODE_KEY, py_license)
                            
                            result_tuple = CSharpEnvironmentManager.GetAllEnvironmentVariables()
                            resource_name = getattr(result_tuple, 'Item1', None) or ""
                            machine_token = getattr(result_tuple, 'Item2', None) or ""
                            secret = getattr(result_tuple, 'Item3', None) or ""
                            license_code = getattr(result_tuple, 'Item4', None) or ""
                        except Exception:
                            return (py_resource, py_token, py_secret, py_license)
                    else:
                        return (py_resource, py_token, py_secret, py_license)
            
            return (resource_name, machine_token, secret, license_code)
                
        except Exception as e:
            return (
                os.environ.get(HexaEightEnvironmentManager.RESOURCENAME_KEY),
                os.environ.get(HexaEightEnvironmentManager.MACHINETOKEN_KEY),
                os.environ.get(HexaEightEnvironmentManager.SECRET_KEY),
                os.environ.get(HexaEightEnvironmentManager.LICENSECODE_KEY)
            )
    
    @staticmethod
    def load_hexaeight_variables_from_env_file(env_file_path, debug_mode: bool = False):
        """Load HexaEight environment variables from a file."""
        _ensure_agent_available()
        
        python_dict = {}
        
        if not os.path.exists(env_file_path):
            raise FileNotFoundError(f"Environment file not found: {env_file_path}")
        
        with open(env_file_path, 'r') as f:
            lines = f.readlines()
        
        hexaeight_keys = [
            HexaEightEnvironmentManager.RESOURCENAME_KEY,
            HexaEightEnvironmentManager.MACHINETOKEN_KEY,
            HexaEightEnvironmentManager.SECRET_KEY,
            HexaEightEnvironmentManager.LICENSECODE_KEY
        ]
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            equals_index = line.find('=')
            if equals_index > 0:
                key = line[:equals_index].strip()
                
                if key in hexaeight_keys:
                    value = line[equals_index + 1:].strip()
                    
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    
                    os.environ[key] = value
                    if key == HexaEightEnvironmentManager.RESOURCENAME_KEY:
                        os.environ[HexaEightEnvironmentManager.RESOURCENAME_KEY2] = value
                    
                    if DOTNET_AVAILABLE:
                        try:
                            Environment.SetEnvironmentVariable(key, value)
                            if key == HexaEightEnvironmentManager.RESOURCENAME_KEY:
                                Environment.SetEnvironmentVariable(
                                    HexaEightEnvironmentManager.RESOURCENAME_KEY2, value
                                )
                        except Exception:
                            pass
                    
                    python_dict[key] = value
        
        try:
            CSharpEnvironmentManager.LoadHexaEightVariablesFromEnvFile(env_file_path)
        except Exception:
            pass
        
        if debug_mode:
            print(f"🔍 ENV DEBUG: Loaded {len(python_dict)} variables from {env_file_path}")
        
        return python_dict
    
    @staticmethod
    def set_resource_name(resource_name, debug_mode: bool = False):
        """Set the resource name environment variable."""
        _ensure_agent_available()
        try:
            os.environ[HexaEightEnvironmentManager.RESOURCENAME_KEY] = resource_name
            os.environ[HexaEightEnvironmentManager.RESOURCENAME_KEY2] = resource_name
            
            result = CSharpEnvironmentManager.SetResourceName(resource_name)
            
            if DOTNET_AVAILABLE:
                try:
                    Environment.SetEnvironmentVariable(HexaEightEnvironmentManager.RESOURCENAME_KEY, resource_name)
                    Environment.SetEnvironmentVariable(HexaEightEnvironmentManager.RESOURCENAME_KEY2, resource_name)
                except Exception:
                    pass
            
            if debug_mode:
                print(f"🔍 ENV DEBUG: Set resource name to: {resource_name}")
            
            return result
            
        except Exception as e:
            if debug_mode:
                print(f"🔍 ENV DEBUG: Error setting resource name: {e}")
            os.environ[HexaEightEnvironmentManager.RESOURCENAME_KEY] = resource_name
            os.environ[HexaEightEnvironmentManager.RESOURCENAME_KEY2] = resource_name
            return "Ok"


# ==================================================================================
# CLEAN HANDOVER AGENT CLASS
# ==================================================================================

class HexaEightAgent:
    """Agent with clean message handover - no content pre-processing."""
    
    def __init__(self, debug_mode: bool = False):
        """
        Initialize HexaEight Agent.
        
        Args:
            debug_mode: If True, enables debug logging. Default is False.
        """
        _ensure_agent_available()
        self._clr_agent_config = CSharpAgentConfig()
        self.debug_mode = debug_mode
        
        self._ensure_environment_loaded()
        
        # Event handling
        self._event_queue = asyncio.Queue()
        self._event_handlers = {}
        self._running_event_loop = False
        
        # Setup C# event handlers
        self._setup_csharp_event_handlers()
    
    def enable_debug(self, enabled: bool = True):
        """Enable or disable debug mode at runtime."""
        self.debug_mode = enabled
        self.debug_log(f"Debug mode {'enabled' if enabled else 'disabled'}")
    
    def debug_log(self, message: str):
        """Debug logging helper."""
        if self.debug_mode:
            print(f"🐛 AGENT DEBUG: {message}")
    
    def _log_info(self, message: str):
        """Info logging (always shown for important information)."""
        print(f"ℹ️  {message}")
    
    def _log_success(self, message: str):
        """Success logging (always shown)."""
        print(f"✅ {message}")
    
    def _log_warning(self, message: str):
        """Warning logging (always shown)."""
        print(f"⚠️ {message}")
    
    def _log_error(self, message: str):
        """Error logging (always shown)."""
        print(f"❌ {message}")
    
    def _ensure_environment_loaded(self):
        """Ensure HexaEight environment variables are loaded."""
        try:
            env_file_path = "env-file"
            if os.path.exists(env_file_path):
                loaded_vars = HexaEightEnvironmentManager.load_hexaeight_variables_from_env_file(
                    env_file_path, self.debug_mode
                )
                self._log_success(f"Loaded {len(loaded_vars)} variables from env-file")
            
            resource_name, machine_token, secret, license_code = (
                HexaEightEnvironmentManager.get_all_environment_variables()
            )
            
            env_vars_to_set = {
                HexaEightEnvironmentManager.RESOURCENAME_KEY: resource_name,
                HexaEightEnvironmentManager.RESOURCENAME_KEY2: resource_name,
                HexaEightEnvironmentManager.MACHINETOKEN_KEY: machine_token,
                HexaEightEnvironmentManager.SECRET_KEY: secret,
                HexaEightEnvironmentManager.LICENSECODE_KEY: license_code
            }
            
            for key, value in env_vars_to_set.items():
                if value:
                    os.environ[key] = value
                    if DOTNET_AVAILABLE:
                        try:
                            Environment.SetEnvironmentVariable(key, value)
                        except Exception:
                            pass
            
            self.debug_log("Environment setup complete")
            
        except Exception as e:
            self._log_warning(f"Error ensuring environment loaded: {e}")
    
    def _setup_csharp_event_handlers(self):
        """Setup C# event handlers for CLEAN handover."""
        try:
            # CLEAN handover - pass raw content with minimal processing
            self._clr_agent_config.MessageReceived += self._on_message_received_clean
            self._clr_agent_config.TaskReceived += self._on_task_received_clean
            self._clr_agent_config.TaskStepReceived += self._on_task_step_received_clean
            self._clr_agent_config.TaskStepUpdated += self._on_task_step_updated_clean
            self._clr_agent_config.TaskCompleted += self._on_task_completed_clean
            self._clr_agent_config.LockExpiredNotification += self._on_lock_expired_clean
            self._clr_agent_config.ScheduledTaskCreationReceived += self._on_scheduled_task_creation_clean
            
            self.debug_log("Clean handover event handlers registered")
            
        except Exception as e:
            self._log_error(f"Error setting up event handlers: {e}")
    
    def _on_message_received_clean(self, sender, e):
        """CLEAN: Pass raw decrypted content to demo handlers."""
        try:
            self.debug_log("=== CLEAN MESSAGE RECEIVED ===")
            self.debug_log(f"Message ID: {e.MessageId}")
            self.debug_log(f"Sender: {e.Sender}")
            self.debug_log(f"Is Task Message: {e.IsTaskMessage}")
            self.debug_log(f"Is From Self: {e.IsFromSelf}")
            self.debug_log(f"Raw Content: {e.DecryptedContent[:200]}...")
            
            event = MessageReceivedEvent(
                topic=e.Topic or "",
                sender=e.Sender or "",
                sender_internal_id=e.SenderInternalId or "",
                decrypted_content=e.DecryptedContent or "",  # RAW content - no processing
                timestamp=e.Timestamp.ToDateTime() if hasattr(e.Timestamp, 'ToDateTime') else datetime.utcnow(),
                message_id=e.MessageId or "",
                is_task_message=e.IsTaskMessage,
                is_from_self=e.IsFromSelf,
                is_schedule_notification=e.IsScheduleNotification,
                is_lock_expired=e.IsLockExpired
            )
            
            # Queue event for demo handlers
            try:
                self._event_queue.put_nowait(('message_received', event))
            except:
                self.debug_log("Event queue full, skipping message event")
                
        except Exception as ex:
            self.debug_log(f"Error in clean message handler: {ex}")
            self._log_error(f"Error in clean message handler: {ex}")
    
    def _on_task_received_clean(self, sender, e):
        """CLEAN: Pass task data to demo handlers."""
        try:
            self.debug_log("=== CLEAN TASK RECEIVED ===")
            self.debug_log(f"Task ID: {e.TaskId}")
            self.debug_log(f"Title: {e.Title}")
            
            event = TaskReceivedEvent(
                task_id=e.TaskId or "",
                title=e.Title or "",
                description=e.Description or "",
                total_steps=e.TotalSteps,
                status=e.Status or "",
                created_by=e.CreatedBy or "",
                created_at=e.CreatedAt.ToDateTime() if hasattr(e.CreatedAt, 'ToDateTime') else datetime.utcnow(),
                message_id=e.MessageId or ""
            )
            
            try:
                self._event_queue.put_nowait(('task_received', event))
            except:
                self.debug_log("Event queue full, skipping task event")
                
        except Exception as ex:
            self.debug_log(f"Error in clean task handler: {ex}")
            self._log_error(f"Error in clean task handler: {ex}")
    
    def _on_task_step_received_clean(self, sender, e):
        """CLEAN: Pass task step data to demo handlers."""
        try:
            self.debug_log("=== CLEAN TASK STEP RECEIVED ===")
            self.debug_log(f"Parent Task ID: {e.ParentTaskId}")
            self.debug_log(f"Step Number: {e.StepNumber}")

            if hasattr(self, '_agent_type') and self._agent_type == "parent":
                self.debug_log("Note: Parent agents should not process task steps - only monitor and coordinate")
                print(f"NOTICE: Parent agents cannot process task steps")
                print(f"   Task steps should be delegated to child agents for integrity")
                print(f"   This ensures separation of duties and prevents self-completion fraud")
                return  # Don't pass the event to demo handlers
            
            event = TaskStepEvent(
                parent_task_id=e.ParentTaskId or "",
                step_number=e.StepNumber,
                description=e.Description or "",
                status=e.Status or "",
                message_id=e.MessageId or "",
                sender=""
            )
            
            try:
                self._event_queue.put_nowait(('task_step_received', event))
            except:
                self.debug_log("Event queue full, skipping task step event")
                
        except Exception as ex:
            self.debug_log(f"Error in clean task step handler: {ex}")
            self._log_error(f"Error in clean task step handler: {ex}")
    
    def _on_task_step_updated_clean(self, sender, e):
        """CLEAN: Pass task step update data to demo handlers."""
        try:
            self.debug_log("=== CLEAN TASK STEP UPDATED ===")
            self.debug_log(f"Parent Task ID: {e.ParentTaskId}")
            self.debug_log(f"Step Number: {e.StepNumber}")
            
            event = TaskStepUpdateEvent(
                parent_task_id=e.ParentTaskId or "",
                step_number=e.StepNumber,
                status=e.Status or "",
                completed_by=e.CompletedBy or "",
                completed_at=e.CompletedAt.ToDateTime() if hasattr(e.CompletedAt, 'ToDateTime') else datetime.utcnow(),
                result=e.Result
            )
            
            try:
                self._event_queue.put_nowait(('task_step_updated', event))
            except:
                self.debug_log("Event queue full, skipping task step update event")
                
        except Exception as ex:
            self.debug_log(f"Error in clean task step update handler: {ex}")
            self._log_error(f"Error in clean task step update handler: {ex}")
    
    def _on_task_completed_clean(self, sender, e):
        """CLEAN: Pass task completion data to demo handlers."""
        try:
            self.debug_log("=== CLEAN TASK COMPLETED ===")
            self.debug_log(f"Task ID: {e.TaskId}")
            
            event = TaskCompleteEvent(
                task_id=e.TaskId or "",
                completed_by=e.CompletedBy or "",
                completed_at=e.CompletedAt.ToDateTime() if hasattr(e.CompletedAt, 'ToDateTime') else datetime.utcnow()
            )
            
            try:
                self._event_queue.put_nowait(('task_completed', event))
            except:
                self.debug_log("Event queue full, skipping task completed event")
                
        except Exception as ex:
            self.debug_log(f"Error in clean task completed handler: {ex}")
            self._log_error(f"Error in clean task completed handler: {ex}")
    
    def _on_lock_expired_clean(self, sender, e):
        """CLEAN: Pass lock expiration data to demo handlers."""
        try:
            self.debug_log("=== CLEAN LOCK EXPIRED ===")
            self.debug_log(f"Message ID: {e.MessageId}")
            
            event = MessageReceivedEvent(
                topic="",
                sender="SYSTEM",
                sender_internal_id="",
                decrypted_content="",
                timestamp=e.Timestamp.ToDateTime() if hasattr(e.Timestamp, 'ToDateTime') else datetime.utcnow(),
                message_id=e.MessageId or "",
                is_lock_expired=True
            )
            
            try:
                self._event_queue.put_nowait(('lock_expired', event))
            except:
                self.debug_log("Event queue full, skipping lock expired event")
                
        except Exception as ex:
            self.debug_log(f"Error in clean lock expired handler: {ex}")
            self._log_error(f"Error in clean lock expired handler: {ex}")
    
    def _on_scheduled_task_creation_clean(self, sender, e):
        """CLEAN: Pass scheduled task creation data to demo handlers."""
        try:
            self.debug_log("=== CLEAN SCHEDULED TASK CREATION ===")
            self.debug_log(f"Task ID: {e.TaskId}")
            self.debug_log(f"Title: {e.Title}")
            self.debug_log(f"Scheduled By: {e.ScheduledBy}")
            
            # Convert C# List<string> to Python list
            steps = []
            if hasattr(e, 'Steps') and e.Steps:
                for step in e.Steps:
                    steps.append(str(step))
            
            event = ScheduledTaskCreationEvent(
                task_id=e.TaskId or "",
                title=e.Title or "",
                description=e.Description or "",
                steps=steps,
                scheduled_by=e.ScheduledBy or "",
                scheduled_by_internal_id=e.ScheduledByInternalId or "",
                original_schedule_time=e.OriginalScheduleTime.ToDateTime() if hasattr(e.OriginalScheduleTime, 'ToDateTime') else datetime.utcnow()
            )
            
            try:
                self._event_queue.put_nowait(('scheduled_task_creation', event))
            except:
                self.debug_log("Event queue full, skipping scheduled task creation event")
                
        except Exception as ex:
            self.debug_log(f"Error in clean scheduled task creation handler: {ex}")
            self._log_error(f"Error in clean scheduled task creation handler: {ex}")
    
    # ==================================================================================
    # BASIC AGENT METHODS (unchanged)
    # ==================================================================================
    
    def set_client_credentials(self, client_id: str, token_server_url: str, logging: bool = False):
        """Set client credentials."""
        self.debug_log(f"Setting client credentials for {client_id}")
        self._ensure_environment_loaded()
        self._clr_agent_config.SetClientCredentials(client_id, token_server_url, logging)
    
    def activate_parent_agent(self) -> bool:
        """Activate parent agent."""
        self.debug_log("Activating parent agent")
        self._ensure_environment_loaded()
        result = self._clr_agent_config.ActivateParentAgent()
        if result:
            self._log_success("Parent agent activated")
        else:
            self._log_error("Failed to activate parent agent")
        return result
    
    def create_ai_parent_agent(self, filename: str, loadenv: bool = False, 
                              client_id: str = "", token_server_url: str = "", 
                              logging: bool = False) -> bool:
        """Create AI parent agent and save configuration."""
        self.debug_log(f"Creating AI parent agent with file: {filename}")
        self._ensure_environment_loaded()
        result = self._clr_agent_config.CreateAIParentAgent(filename, loadenv, client_id, token_server_url, logging)
        if result:
            self._log_success(f"AI parent agent created and saved to {filename}")
        else:
            self._log_error("Failed to create AI parent agent")
        return result
    
    def load_ai_parent_agent(self, filename: str, loadenv: bool = False,
                            client_id: str = "", token_server_url: str = "",
                            logging: bool = False) -> bool:
        """Load AI parent agent configuration."""
        self.debug_log(f"Loading AI parent agent from file: {filename}")
        self._ensure_environment_loaded()
        result = self._clr_agent_config.LoadAIParentAgent(filename, loadenv, client_id, token_server_url, logging)
        if result:
            self._log_success(f"AI parent agent loaded from {filename}")
        else:
            self._log_error("Failed to load AI parent agent")
        return result
    
    def create_ai_child_agent(self, agent_complex_password: str, filename: str, 
                             loadenv: bool = False, client_id: str = "", 
                             token_server_url: str = "", logging: bool = False) -> bool:
        """Create AI child agent and save configuration."""
        self.debug_log(f"Creating AI child agent with file: {filename}")
        self._ensure_environment_loaded()
        result = self._clr_agent_config.CreateAIChildAgent(agent_complex_password, filename, loadenv, client_id, token_server_url, logging)
        if result:
            self._log_success(f"AI child agent created and saved to {filename}")
        else:
            self._log_error("Failed to create AI child agent")
        return result
    
    def load_ai_child_agent(self, agent_password: str, filename: str, 
                           loadenv: bool = False, client_id: str = "", 
                           token_server_url: str = "", logging: bool = False) -> bool:
        """Load AI child agent configuration."""
        self.debug_log(f"Loading AI child agent from file: {filename}")
        self._ensure_environment_loaded()
        result = self._clr_agent_config.LoadAIChildAgent(agent_password, filename, loadenv, client_id, token_server_url, logging)
        if result:
            self._log_success(f"AI child agent loaded from {filename}")
        else:
            self._log_error("Failed to load AI child agent")
        return result
    
    async def get_agent_name(self) -> str:
        """Get agent name asynchronously."""
        try:
            task = self._clr_agent_config.GetAgentname()
            if hasattr(task, 'IsCompleted') and task.IsCompleted:
                result = task.Result or ""
            else:
                result = await asyncio.get_event_loop().run_in_executor(None, lambda: task.Result)
            
            self.debug_log(f"Agent name: {result}")
            return result
        except Exception as e:
            self.debug_log(f"Error getting agent name: {e}")
            return ""
    
    def get_internal_identity(self) -> str:
        """Get agent's internal identity."""
        identity = self._clr_agent_config.GetInternalIdentity() or ""
        self.debug_log(f"Internal identity: {identity[:8]}...")
        return identity
    
    # ==================================================================================
    # PUBSUB METHODS (unchanged)
    # ==================================================================================
    
    async def connect_to_pubsub(self, pubsub_server_url: str, agent_type: str = "child") -> bool:
        """Connect to PubSub server asynchronously."""
        try:
            self.debug_log(f"Connecting to PubSub server: {pubsub_server_url}")
            task = self._clr_agent_config.ConnectToPubSubAsync(pubsub_server_url, agent_type)
            result = await asyncio.get_event_loop().run_in_executor(None, lambda: task.Result)
            
            if result:
                self._log_success(f"Connected to PubSub server: {pubsub_server_url}")
            else:
                self._log_error(f"Failed to connect to PubSub server: {pubsub_server_url}")
            
            return result
        except Exception as e:
            self._log_error(f"Error connecting to PubSub: {e}")
            return False
    
    def is_connected_to_pubsub(self) -> bool:
        """Check if connected to PubSub server."""
        connected = self._clr_agent_config.IsConnectedToPubSub()
        self.debug_log(f"PubSub connection status: {connected}")
        return connected
    
    def disconnect_from_pubsub(self):
        """Disconnect from PubSub server."""
        self.debug_log("Disconnecting from PubSub server")
        self._clr_agent_config.DisconnectFromPubSub()
        self._log_info("Disconnected from PubSub server")
    
    async def publish_to_self(self, pubsub_server_url: str, message: str) -> bool:
        """Publish message to self."""
        try:
            self.debug_log(f"Publishing to self: {message[:50]}...")
            task = self._clr_agent_config.PublishToSelfAsync(pubsub_server_url, message)
            result = await asyncio.get_event_loop().run_in_executor(None, lambda: task.Result)
            
            if result:
                self.debug_log("Message published to self successfully")
            else:
                self.debug_log("Failed to publish message to self")
            
            return result
        except Exception as e:
            self._log_error(f"Error publishing to self: {e}")
            return False
    
    async def publish_to_agent(self, pubsub_server_url: str, target_agent_name: str, message: str) -> bool:
        """Publish message to specific agent by name."""
        try:
            self.debug_log(f"Publishing to agent {target_agent_name}: {message[:50]}...")
            task = self._clr_agent_config.PublishToAgentAsync(pubsub_server_url, target_agent_name, message)
            result = await asyncio.get_event_loop().run_in_executor(None, lambda: task.Result)
            
            if result:
                self.debug_log(f"Message published to {target_agent_name} successfully")
            else:
                self.debug_log(f"Failed to publish message to {target_agent_name}")
            
            return result
        except Exception as e:
            self._log_error(f"Error publishing to agent: {e}")
            return False
    
    async def publish_to_internal_id(self, pubsub_server_url: str, target_internal_id: str, message: str) -> bool:
        """Publish message to specific agent by internal ID."""
        try:
            self.debug_log(f"Publishing to internal ID {target_internal_id[:8]}...: {message[:50]}...")
            task = self._clr_agent_config.PublishToInternalIdAsync(pubsub_server_url, target_internal_id, message)
            result = await asyncio.get_event_loop().run_in_executor(None, lambda: task.Result)
            
            if result:
                self.debug_log("Message published to internal ID successfully")
            else:
                self.debug_log("Failed to publish message to internal ID")
            
            return result
        except Exception as e:
            self._log_error(f"Error publishing to internal ID: {e}")
            return False
    
    async def publish_broadcast(self, pubsub_server_url: str, message: str) -> bool:
        """Broadcast message to all connected agents."""
        try:
            self.debug_log(f"Broadcasting message: {message[:50]}...")
            task = self._clr_agent_config.PublishBroadcastAsync(pubsub_server_url, message)
            result = await asyncio.get_event_loop().run_in_executor(None, lambda: task.Result)
            
            if result:
                self.debug_log("Broadcast message sent successfully")
            else:
                self.debug_log("Failed to send broadcast message")
            
            return result
        except Exception as e:
            self._log_error(f"Error broadcasting: {e}")
            return False
    
    # ==================================================================================
    # MESSAGE LOCKING METHODS (unchanged)
    # ==================================================================================
    
    async def lock_message(self, pubsub_server_url: str, message_id: str) -> bool:
        """Lock a message for exclusive processing."""
        try:
            self.debug_log(f"Locking message: {message_id}")
            task = self._clr_agent_config.LockMessageAsync(pubsub_server_url, message_id)
            result = await asyncio.get_event_loop().run_in_executor(None, lambda: task.Result)
            
            if result:
                self.debug_log(f"Message {message_id} locked successfully")
            else:
                self.debug_log(f"Failed to lock message {message_id}")
            
            return result
        except Exception as e:
            self._log_error(f"Error locking message: {e}")
            return False
    
    async def release_lock(self, pubsub_server_url: str, message_id: str) -> bool:
        """Release a message lock."""
        try:
            self.debug_log(f"Releasing lock for message: {message_id}")
            task = self._clr_agent_config.ReleaseLockAsync(pubsub_server_url, message_id)
            result = await asyncio.get_event_loop().run_in_executor(None, lambda: task.Result)
            
            if result:
                self.debug_log(f"Lock released for message {message_id}")
            else:
                self.debug_log(f"Failed to release lock for message {message_id}")
            
            return result
        except Exception as e:
            self._log_error(f"Error releasing lock: {e}")
            return False
    
    async def send_lock_heartbeat(self, pubsub_server_url: str, message_id: str) -> bool:
        """Send heartbeat to maintain message lock."""
        try:
            self.debug_log(f"Sending heartbeat for message: {message_id}")
            task = self._clr_agent_config.SendLockHeartbeatAsync(pubsub_server_url, message_id)
            result = await asyncio.get_event_loop().run_in_executor(None, lambda: task.Result)
            
            if not result:
                self.debug_log(f"Failed to send heartbeat for message {message_id}")
            
            return result
        except Exception as e:
            self._log_error(f"Error sending lock heartbeat: {e}")
            return False
    
    def get_active_locks(self) -> List[MessageLock]:
        """Get list of active message locks."""
        try:
            csharp_locks = self._clr_agent_config.GetActiveLocks()
            locks = []
            for lock in csharp_locks:
                locks.append(MessageLock(
                    message_id=lock.MessageId or "",
                    locked_by=lock.LockedBy or "",
                    locked_by_internal_id=lock.LockedByInternalId or "",
                    locked_at=lock.LockedAt.ToDateTime() if hasattr(lock.LockedAt, 'ToDateTime') else datetime.utcnow(),
                    expires_at=lock.ExpiresAt.ToDateTime() if hasattr(lock.ExpiresAt, 'ToDateTime') else datetime.utcnow()
                ))
            
            self.debug_log(f"Active locks: {len(locks)}")
            return locks
        except Exception as e:
            self._log_error(f"Error getting active locks: {e}")
            return []
    
    # ==================================================================================
    # TASK MANAGEMENT METHODS (unchanged)
    # ==================================================================================
    
    def create_task_message(self, title: str, description: str, step_descriptions: List[str]) -> TaskInfo:
        """Create a task message."""
        try:
            self.debug_log(f"Creating task message: {title}")
            csharp_list = CSharpList[str]()
            for step in step_descriptions:
                csharp_list.Add(step)
            
            task_msg = self._clr_agent_config.CreateTaskMessage(title, description, csharp_list)
            
            steps = []
            for i, desc in enumerate(step_descriptions):
                steps.append(TaskStep(
                    step_number=i + 1,
                    description=desc
                ))
            
            return TaskInfo(
                task_id=task_msg.TaskId or "",
                title=task_msg.Title or "",
                description=task_msg.Description or "",
                steps=steps,
                created_by=task_msg.CreatedBy or "",
                created_by_internal_id=task_msg.CreatedByInternalId or ""
            )
        except Exception as e:
            self._log_error(f"Error creating task message: {e}")
            return TaskInfo(task_id="", title="", description="")
    
    async def publish_task(self, pubsub_server_url: str, task_message: TaskInfo) -> bool:
        """Publish a task message."""
        try:
            self.debug_log(f"Publishing task: {task_message.title}")
            # Convert Python TaskInfo to C# TaskMessage
            csharp_task = self._clr_agent_config.CreateTaskMessage(
                task_message.title, 
                task_message.description, 
                CSharpList[str]([step.description for step in task_message.steps])
            )
            
            task = self._clr_agent_config.PublishTaskAsync(pubsub_server_url, csharp_task)
            result = await asyncio.get_event_loop().run_in_executor(None, lambda: task.Result)
            
            if result:
                self.debug_log(f"Task {task_message.title} published successfully")
            else:
                self.debug_log(f"Failed to publish task {task_message.title}")
            
            return result
        except Exception as e:
            self._log_error(f"Error publishing task: {e}")
            return False
    
    async def create_and_lock_task(self, pubsub_server_url: str, title: str,
                                  description: str, step_descriptions: List[str]) -> Optional[Tuple[str, str]]:
        """Create and lock a task for monitoring."""
        try:
            self.debug_log(f"Creating and locking task: {title}")
            csharp_list = CSharpList[str]()
            for step in step_descriptions:
                csharp_list.Add(step)

            task = self._clr_agent_config.CreateAndLockTaskAsync(pubsub_server_url, title, description, csharp_list)
            result = await asyncio.get_event_loop().run_in_executor(None, lambda: task.Result)

            if result is not None:
                # Handle ValueTuple access robustly for Python.NET
                try:
                    # Try different access methods
                    if hasattr(result, 'Item1') and hasattr(result, 'Item2'):
                        task_result = (result.Item1, result.Item2)
                    elif hasattr(result, '__getitem__'):
                        task_result = (result[0], result[1])
                    else:
                        # Parse from string representation as fallback
                        result_str = str(result)
                        if '(' in result_str and ')' in result_str:
                            parts = result_str.strip('()').split(',')
                            if len(parts) >= 2:
                                task_result = (parts[0].strip(), parts[1].strip())
                            else:
                                task_result = None
                        else:
                            task_result = None
                    
                    if task_result:
                        self.debug_log(f"Task created and locked: {task_result[0]}")
                    
                    return task_result
                except Exception as e:
                    self.debug_log(f"Error accessing ValueTuple: {e}")

            self.debug_log("Failed to create and lock task")
            return None
        except Exception as e:
            self._log_error(f"Error creating and locking task: {e}")
            return None

    async def update_task_step_completion(self, pubsub_server_url: str, parent_task_id: str,
                                    step_number: int, result: Any) -> bool:
        """Update task step completion - FIXED: Convert result to JSON string."""
        try:
            self.debug_log(f"Updating task step completion: {parent_task_id} step {step_number}")

            # FIXED: Convert the result to JSON string to avoid IntPtr serialization issues
            if isinstance(result, dict):
                # Convert Python dict to JSON string
                result_json = json.dumps(result, default=str, ensure_ascii=False)
                self.debug_log(f"Converted result dict to JSON string")
            elif isinstance(result, str):
                # Already a string, use as-is
                result_json = result
            else:
                # Convert other types to JSON string
                result_json = json.dumps(result, default=str, ensure_ascii=False)

            task = self._clr_agent_config.UpdateTaskStepCompletionAsync(pubsub_server_url, parent_task_id, step_number, result_json)
            completion_result = await asyncio.get_event_loop().run_in_executor(None, lambda: task.Result)

            if completion_result:
                self.debug_log(f"Task step {step_number} completion updated successfully")
            else:
                self.debug_log(f"Failed to update task step {step_number} completion")

            return completion_result
        except Exception as e:
            self._log_error(f"Error updating task step completion: {e}")
            return False

    async def complete_task(self, pubsub_server_url: str, task_id: str, message_id: str) -> bool:
        """Complete a task and release its lock."""
        try:
            self.debug_log(f"Completing task: {task_id}")
            task = self._clr_agent_config.CompleteTaskAsync(pubsub_server_url, task_id, message_id)
            result = await asyncio.get_event_loop().run_in_executor(None, lambda: task.Result)
            
            if result:
                self.debug_log(f"Task {task_id} completed successfully")
            else:
                self.debug_log(f"Failed to complete task {task_id}")
            
            return result
        except Exception as e:
            self._log_error(f"Error completing task: {e}")
            return False
    
    # ==================================================================================
    # MESSAGE SCHEDULING METHODS (unchanged)
    # ==================================================================================
    
    async def schedule_message(self, pubsub_server_url: str, scheduled_for: datetime, 
                              target_type: str, target_value: str, message: str, 
                              message_type: str = "message") -> bool:
        """Schedule a message for future delivery."""
        try:
            self.debug_log(f"Scheduling message for {scheduled_for}: {message[:50]}...")
            # Convert Python datetime to C# DateTime
            csharp_datetime = DateTime(
                scheduled_for.year, scheduled_for.month, scheduled_for.day,
                scheduled_for.hour, scheduled_for.minute, scheduled_for.second
            )
            
            task = self._clr_agent_config.ScheduleMessageAsync(
                pubsub_server_url, csharp_datetime, target_type, target_value, message, message_type
            )
            result = await asyncio.get_event_loop().run_in_executor(None, lambda: task.Result)
            
            if result:
                self.debug_log("Message scheduled successfully")
            else:
                self.debug_log("Failed to schedule message")
            
            return result
        except Exception as e:
            self._log_error(f"Error scheduling message: {e}")
            return False
    
    # ==================================================================================
    # LLM GATEWAY METHODS (unchanged)
    # ==================================================================================
    
    async def send_llm_request(self, pubsub_server_url: str, llm_request: LLMRequest) -> bool:
        """Send an LLM request to available gateways."""
        try:
            self.debug_log(f"Sending LLM request: {llm_request.provider}/{llm_request.model}")
            # Convert Python LLMRequest to C# format
            import json
            request_dict = {
                "requestId": llm_request.request_id,
                "provider": llm_request.provider,
                "model": llm_request.model,
                "messages": [{"role": msg.role, "content": msg.content} for msg in llm_request.messages],
                "maxTokens": llm_request.max_tokens,
                "temperature": llm_request.temperature,
                "requesterInternalId": llm_request.requester_internal_id
            }
            
            # Send as JSON string to agent
            task = self._clr_agent_config.SendSimpleLLMRequestAsync(
                pubsub_server_url, llm_request.provider, llm_request.model, 
                json.dumps(request_dict), llm_request.max_tokens
            )
            result = await asyncio.get_event_loop().run_in_executor(None, lambda: task.Result)
            
            if result:
                self.debug_log("LLM request sent successfully")
            else:
                self.debug_log("Failed to send LLM request")
            
            return result
        except Exception as e:
            self._log_error(f"Error sending LLM request: {e}")
            return False
    
    async def get_available_providers(self, pubsub_server_url: str) -> List[str]:
        """Get available AI providers."""
        try:
            self.debug_log("Getting available providers")
            task = self._clr_agent_config.GetAvailableProvidersAsync(pubsub_server_url)
            providers = await asyncio.get_event_loop().run_in_executor(None, lambda: task.Result)
            provider_list = list(providers) if providers else []
            
            self.debug_log(f"Available providers: {provider_list}")
            return provider_list
        except Exception as e:
            self._log_error(f"Error getting providers: {e}")
            return []
    
    # ==================================================================================
    # HEALTH AND STATS METHODS (unchanged)
    # ==================================================================================
    
    async def get_server_health(self, pubsub_server_url: str) -> str:
        """Get server health status."""
        try:
            self.debug_log(f"Getting server health from {pubsub_server_url}")
            task = self._clr_agent_config.GetServerHealthAsync(pubsub_server_url)
            result = await asyncio.get_event_loop().run_in_executor(None, lambda: task.Result)
            return result
        except Exception as e:
            error_msg = f"Error getting health: {e}"
            self._log_error(error_msg)
            return error_msg
    
    async def get_server_stats(self, pubsub_server_url: str) -> str:
        """Get server statistics."""
        try:
            self.debug_log(f"Getting server stats from {pubsub_server_url}")
            task = self._clr_agent_config.GetServerStatsAsync(pubsub_server_url)
            result = await asyncio.get_event_loop().run_in_executor(None, lambda: task.Result)
            return result
        except Exception as e:
            error_msg = f"Error getting stats: {e}"
            self._log_error(error_msg)
            return error_msg
    
    # ==================================================================================
    # EVENT HANDLING METHODS - CLEAN HANDOVER
    # ==================================================================================
    
    async def events(self) -> AsyncGenerator[Tuple[str, Any], None]:
        """
        Async generator that yields events as they occur.
        
        Usage:
            async for event_type, event_data in agent.events():
                if event_type == 'message_received':
                    print(f"Message from {event_data.sender}: {event_data.decrypted_content}")
                elif event_type == 'task_received':
                    print(f"New task: {event_data.title}")
                elif event_type == 'scheduled_task_creation':
                    print(f"Scheduled task creation: {event_data.title}")
        """
        while True:
            try:
                event_type, event_data = await self._event_queue.get()
                self.debug_log(f"Event yielded: {event_type}")
                yield event_type, event_data
            except asyncio.CancelledError:
                self.debug_log("Event loop cancelled")
                break
            except Exception as e:
                self._log_error(f"Error in event loop: {e}")
                await asyncio.sleep(0.1)
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register a callback handler for specific event types."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
        self.debug_log(f"Registered handler for {event_type}")
    
    def unregister_event_handler(self, event_type: str, handler: Callable):
        """Unregister an event handler."""
        if event_type in self._event_handlers:
            try:
                self._event_handlers[event_type].remove(handler)
                self.debug_log(f"Unregistered handler for {event_type}")
            except ValueError:
                self.debug_log(f"Handler not found for {event_type}")
    
    async def start_event_processing(self):
        """Start processing events with registered handlers."""
        if self._running_event_loop:
            self.debug_log("Event processing already running")
            return
        
        self._running_event_loop = True
        self.debug_log("Starting event processing")
        
        async for event_type, event_data in self.events():
            if not self._running_event_loop:
                break
            
            if event_type in self._event_handlers:
                for handler in self._event_handlers[event_type]:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(event_data)
                        else:
                            handler(event_data)
                    except Exception as e:
                        self._log_error(f"Error in event handler: {e}")
    
    def stop_event_processing(self):
        """Stop event processing."""
        self._running_event_loop = False
        self.debug_log("Event processing stopped")
    
    # ==================================================================================
    # CONTEXT MANAGER SUPPORT (unchanged)
    # ==================================================================================
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.disconnect_from_pubsub()
        self.stop_event_processing()
    
    def dispose(self):
        """Dispose of resources."""
        self.debug_log("Disposing agent resources")
        self.disconnect_from_pubsub()
        self.stop_event_processing()
        if hasattr(self._clr_agent_config, 'Dispose'):
            self._clr_agent_config.Dispose()


# ==================================================================================
# CONVENIENCE ALIASES AND BACKWARDS COMPATIBILITY
# ==================================================================================

# Main agent class alias
HexaEightAgentConfig = HexaEightAgent

# Legacy compatibility classes (deprecated)
class HexaEightJWT:
    def __init__(self, token=None):
        print("Warning: HexaEightJWT is deprecated. Use HexaEightAgent.get_session() instead.")

class HexaEightConfig:
    def __init__(self, app_login_token="", resource_identity=""):
        print("Warning: HexaEightConfig is deprecated. Use HexaEightAgent methods instead.")

class HexaEightConfiguration:
    @staticmethod
    def save(login_token, encrypted_resource_id, filename):
        print("Warning: HexaEightConfiguration.save() is deprecated. Use HexaEightAgent.create_ai_parent_agent() instead.")
        return False
    
    @staticmethod
    def clean(filename):
        print("Warning: HexaEightConfiguration.clean() is deprecated.")
        return False
    
    @staticmethod
    def read(filename):
        print("Warning: HexaEightConfiguration.read() is deprecated. Use HexaEightAgent.load_ai_parent_agent() instead.")
        return HexaEightConfig()


# ==================================================================================
# GLOBAL DEBUG CONTROL FUNCTIONS
# ==================================================================================

def enable_library_debug(enabled: bool = True):
    """Enable or disable library-level debug logging."""
    global LIBRARY_DEBUG
    LIBRARY_DEBUG = enabled
    if enabled:
        print("🔧 Library debug mode enabled")
    else:
        print("🔧 Library debug mode disabled")

def is_library_debug_enabled() -> bool:
    """Check if library debug mode is enabled."""
    return LIBRARY_DEBUG

# ==================================================================================
# EXAMPLE FILES ACCESS HELPER
# ==================================================================================

def show_examples():
    """Shows how to access included example files."""
    import os
    import hexaeight_agent
    
    package_dir = os.path.dirname(hexaeight_agent.__file__)
    demo_path = os.path.join(package_dir, "demo", "hexaeight_demo.py")
    create_parent = os.path.join(package_dir, "create", "create-identity-for-parent-agent.csx")
    create_child = os.path.join(package_dir, "create", "create-identity-for-child-agent.csx")
    
    print("🚀 HexaEight Agent - Included Examples:")
    print(f"📁 Package location: {package_dir}")
    print(f"🐍 Demo script: {demo_path}")
    print(f"📜 Parent agent script: {create_parent}")
    print(f"📜 Child agent script: {create_child}")
    print("\nTo copy files to current directory:")
    print(">>> import shutil")
    print(f">>> shutil.copy('{demo_path}', '.')")

def get_demo_path():
    """Returns the path to the demo script."""
    import os
    import hexaeight_agent
    package_dir = os.path.dirname(hexaeight_agent.__file__)
    return os.path.join(package_dir, "demo", "hexaeight_demo.py")

def get_create_scripts_path():
    """Returns the path to the create scripts directory."""
    import os
    import hexaeight_agent
    package_dir = os.path.dirname(hexaeight_agent.__file__)
    return os.path.join(package_dir, "create")
