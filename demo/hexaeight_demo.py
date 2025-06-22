#!/usr/bin/env python3
"""
HexaEight Interactive Agent Demo - Python Version (FIXED)

Fixed version with proper task completion handling to prevent race conditions.
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import argparse
import signal
import time
from concurrent.futures import ThreadPoolExecutor

# Import the HexaEight agent wrapper
try:
    from hexaeight_agent import (
        HexaEightAgent, 
        HexaEightEnvironmentManager,
        MessageReceivedEvent,
        TaskReceivedEvent,
        TaskStepEvent,
        TaskStepUpdateEvent,
        TaskCompleteEvent,
        ScheduledTaskCreationEvent
    )
except ImportError as e:
    print(f"❌ Error importing hexaeight_agent: {e}")
    print("Please ensure hexaeight_agent.py is in the same directory")
    sys.exit(1)

# ==================================================================================
# DATA CLASSES
# ==================================================================================

@dataclass
class IncomingMessage:
    id: int
    message_id: str
    sender: str
    content: str
    received_at: datetime
    is_locked: bool = False
    is_task: bool = False
    is_task_step: bool = False
    is_completed: bool = False
    task_id: Optional[str] = None
    step_number: int = 0
    is_from_self: bool = False

@dataclass
class SubTaskInfo:
    step_number: int
    description: str
    status: str = "pending"  # pending, in_progress, completed
    completed_by: Optional[str] = None
    completed_at: Optional[datetime] = None
    message_id: Optional[str] = None

@dataclass
class TaskInfo:
    task_id: str
    message_id: str
    title: str
    total_steps: int
    completed_steps: int = 0
    status: str = "in_progress"
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    sub_tasks: List[SubTaskInfo] = field(default_factory=list)
    # FIXED: Add completion tracking
    is_completing: bool = False
    completion_method: str = ""  # "auto" or "manual"

@dataclass
class AgentConfiguration:
    config_file: str
    agent_type: str
    pubsub_url: str

# ==================================================================================
# MAIN DEMO CLASS
# ==================================================================================

class HexaEightAgentDemo:
    def __init__(self):
        self.agent: Optional[HexaEightAgent] = None
        self.pubsub_url = ""
        self.agent_type = ""
        self.agent_name = ""
        
        # Message tracking
        self.incoming_messages: Dict[str, IncomingMessage] = {}
        self.sent_messages: List[str] = []
        self.active_tasks: Dict[str, TaskInfo] = {}
        self.pending_acknowledgments: Dict[str, str] = {}  # MessageId -> TaskId
        self.message_counter = 0
        
        # FIXED: Add task completion synchronization
        self.task_completion_locks: Dict[str, asyncio.Lock] = {}
        
        # Reconnection tracking
        self.is_reconnecting = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.processed_scheduled_tasks = set()
        
        # Event loop and executor
        self.loop = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.running = True

    def show_welcome(self):
        """Show welcome banner"""
        print("\n" + "="*60)
        print("🤖 HexaEight Interactive Agent Demo - Python Version (FIXED)")
        print("Interactive Agent Coordination Demo")
        print("Type messages, lock them, create tasks - see real agent interaction!")
        print("="*60 + "\n")

    def get_agent_config(self, args) -> Optional[AgentConfiguration]:
        """Get agent configuration from args or user input"""
        if len(args) >= 3:
            config_file = args[1]
            agent_type = args[2].lower()
        else:
            config_file = input("Agent config file: ").strip()
            print("Agent type:")
            print("1. parent")
            print("2. child")
            choice = input("Select (1-2): ").strip()
            agent_type = "parent" if choice == "1" else "child"

        if not os.path.exists(config_file):
            print(f"❌ File not found: {config_file}")
            return None

        pubsub_url = os.environ.get("HEXAEIGHT_PUBSUB_URL", "http://localhost:5000")
        
        return AgentConfiguration(
            config_file=config_file,
            agent_type=agent_type,
            pubsub_url=pubsub_url
        )

    async def initialize_agent(self, config: AgentConfiguration) -> bool:
        """Initialize the HexaEight agent"""
        try:
            self.agent = HexaEightAgent()
            # self.agent.enable_debug(True)  # Enable debug mode
            
            # Load environment if needed
            if config.agent_type == "parent":
                try:
                    env_vars = HexaEightEnvironmentManager.load_hexaeight_variables_from_env_file("env-file")
                    print(f"✅ Loaded {len(env_vars)} environment variables")
                except:
                    print("⚠️ No env-file found, using existing environment")

            # Set client credentials
            client_id = os.environ.get("HEXAEIGHT_CLIENT_ID", "")
            token_server_url = os.environ.get("HEXAEIGHT_TOKENSERVER_URL", "")
            self.agent.set_client_credentials(client_id, token_server_url)

            print(f"🔄 Loading {config.agent_type} agent...")

            # Load agent based on type
            if config.agent_type == "parent":
                success = self.agent.load_ai_parent_agent(
                    config.config_file, True, client_id, token_server_url
                )
            else:
                password = input("Child agent password: ").strip()
                success = self.agent.load_ai_child_agent(
                    password, config.config_file, True, client_id, token_server_url
                )

            if success:
                self.agent_name = await self.agent.get_agent_name()
                internal_id = self.agent.get_internal_identity()
                
                # FIXED: Set agent type in the C# wrapper so scheduled tasks work
                self.agent._clr_agent_config.SetAgentType(config.agent_type)
                
                print(f"✅ Agent: {self.agent_name} ({config.agent_type})")
                print(f"📋 Internal ID: {internal_id[:20]}...")
                print(f"🔧 Agent type set in C# wrapper: {config.agent_type}")
                return True
            else:
                print("❌ Failed to load agent")
                return False

        except Exception as e:
            print(f"❌ Error initializing agent: {e}")
            return False

    def setup_event_handlers(self):
        """Setup event handlers for clean message processing"""
        print("🔗 Setting up event handlers...")
        
        # Register event handlers using the clean handover system
        self.agent.register_event_handler('message_received', self.on_message_received)
        self.agent.register_event_handler('task_received', self.on_task_received)
        self.agent.register_event_handler('task_step_received', self.on_task_step_received)
        self.agent.register_event_handler('task_step_updated', self.on_task_step_updated)
        self.agent.register_event_handler('task_completed', self.on_task_completed)
        self.agent.register_event_handler('lock_expired', self.on_lock_expired)
        
        # FIXED: Register scheduled task creation event handler
        self.agent.register_event_handler('scheduled_task_creation', self.on_scheduled_task_creation)
        
        print("✅ Event handlers registered")

    # FIXED: Add helper method to get or create task completion lock
    def get_task_completion_lock(self, task_id: str) -> asyncio.Lock:
        """Get or create a completion lock for a specific task"""
        if task_id not in self.task_completion_locks:
            self.task_completion_locks[task_id] = asyncio.Lock()
        return self.task_completion_locks[task_id]

    async def on_scheduled_task_creation(self, event: ScheduledTaskCreationEvent):
        """FIXED: Handle scheduled task creation events from C# wrapper"""
        try:
            print(f"\n⏰ SCHEDULED TASK EVENT RECEIVED!")
            print(f"   Title: {event.title}")
            print(f"   Steps: {len(event.steps)}")
            print(f"   Scheduled by: {event.scheduled_by}")
            print(f"   Task ID: {event.task_id}")
            print(f"   Scheduled by internal ID: {event.scheduled_by_internal_id}")
            print(f"   Current agent internal ID: {self.agent.get_internal_identity()}")
            
            # Verify this is for this agent instance
            if event.scheduled_by_internal_id != self.agent.get_internal_identity():
                print(f"⚠️ Ignoring scheduled task - not for this agent instance")
                return
            
            # Check for duplicates
            if event.task_id in self.processed_scheduled_tasks:
                print(f"⚠️ Scheduled task already processed - skipping duplicate")
                return
            
            self.processed_scheduled_tasks.add(event.task_id)
            
            print(f"✅ Processing scheduled task creation...")
            
            # Create the actual task
            result = await self.agent.create_and_lock_task(
                self.pubsub_url, event.title, event.description, event.steps
            )
            
            if result:
                task_id, message_id = result
                print(f"✅ Scheduled task created and locked successfully!")
                print(f"   Created Task ID: {task_id[:8]}...")
                print(f"   Message ID: {message_id[:8]}...")
                
                # Add to local tracking
                self.active_tasks[task_id] = TaskInfo(
                    task_id=task_id,
                    message_id=message_id,
                    title=event.title,
                    total_steps=len(event.steps),
                    status="in_progress",
                    created_by=self.agent_name,
                    created_at=datetime.now(),
                    sub_tasks=[]
                )
                
                print(f"📋 Scheduled task '{event.title}' is now active with {len(event.steps)} steps")
            else:
                print("❌ Failed to create scheduled task")
                self.processed_scheduled_tasks.discard(event.task_id)
            
            print("\n> ", end="", flush=True)
            
        except Exception as e:
            print(f"❌ Error handling scheduled task creation event: {e}")
            print("\n> ", end="", flush=True)

    async def on_message_received(self, event: MessageReceivedEvent):
        """Handle incoming messages with clean handover - FIXED to work with scheduled tasks"""
        try:
            print(f"📨 Processing message from {event.sender}")
            print(f"🐛 DEBUG: Message received from {event.sender}")
            print(f"🐛 DEBUG: Is from self: {event.is_from_self}")
            print(f"🐛 DEBUG: Agent type: {self.agent_type}")
            print(f"🐛 DEBUG: Raw decrypted content: {event.decrypted_content}")
            
            # Skip heartbeats and system messages
            if "💓" in event.decrypted_content or "heartbeat" in event.decrypted_content.lower():
                return
            
            # Parse message content
            actual_content = event.decrypted_content
            
            # Try to parse through HexaEight message format
            try:
                # This should match the Message.Parse logic from C#
                message_data = json.loads(actual_content)
                if isinstance(message_data, dict) and "content" in message_data:
                    actual_content = message_data["content"]
            except:
                pass
            
            # Try to parse as structured message
            try:
                content_json = json.loads(actual_content)
                if isinstance(content_json, dict):
                    message_type = content_json.get("type", "")
                    
                    if message_type == "task":
                        # Store task messages for locking, regardless of sender
                        if event.is_from_self:
                            await self.store_self_task(content_json, event)
                        else:
                            await self.store_received_task(content_json, event)
                        return
                    
                    elif message_type == "task_step":
                        if not event.is_from_self:
                            await self.handle_task_step_message(content_json, event)
                        return
                    
                    elif message_type == "task_step_update":
                        if not event.is_from_self:
                            await self.handle_task_step_update(content_json, event)
                        return
                    
                    elif message_type == "step_acknowledged":
                        if not event.is_from_self:
                            await self.handle_step_acknowledgment(content_json, event)
                        return
                    
                    elif message_type == "step_removal_request":
                        if not event.is_from_self:
                            await self.handle_step_removal_request(content_json, event)
                        return
                    
                    # FIXED: Remove manual scheduled task handling - now handled by event system
                    # The C# Agent.cs will automatically fire the ScheduledTaskCreationReceived event
                    # which is handled by on_scheduled_task_creation above
                    
            except:
                pass
            
            # Skip self messages and empty content
            if event.is_from_self or not actual_content.strip():
                return
            
            # Deduplicate by message ID
            if event.message_id in self.incoming_messages:
                return
            
            # Store regular message
            self.message_counter += 1
            msg = IncomingMessage(
                id=self.message_counter,
                message_id=event.message_id,
                sender=event.sender,
                content=actual_content,
                received_at=event.timestamp,
                is_locked=False
            )
            
            self.incoming_messages[event.message_id] = msg
            
            print(f"\n🔔 NEW MESSAGE #{msg.id} from {msg.sender}")
            print(f"   Content: {msg.content}")
            print(f"   Message ID: {msg.message_id}")
            print("\n> ", end="", flush=True)
            
        except Exception as e:
            print(f"❌ Error processing message: {e}")

    async def store_self_task(self, content_json: dict, event: MessageReceivedEvent):
        """Store self-task for locking capability"""
        try:
            title = content_json.get("title", "Unknown Task")
            if event.message_id not in self.incoming_messages:
                self.message_counter += 1
                task_msg = IncomingMessage(
                    id=self.message_counter,
                    message_id=event.message_id,
                    sender="SELF-TASK",
                    content=f"📋 SELF-TASK: {title}",
                    received_at=event.timestamp,
                    is_task=True,
                    is_from_self=True
                )
                self.incoming_messages[event.message_id] = task_msg
                print(f"📋 Self-task stored for locking: {event.message_id}")
        except Exception as e:
            print(f"❌ Error storing self-task: {e}")

    async def store_received_task(self, content_json: dict, event: MessageReceivedEvent):
        """Store received task for locking capability"""
        try:
            title = content_json.get("title", "Unknown Task")
            total_steps = content_json.get("totalSteps", 0)
            if event.message_id not in self.incoming_messages:
                self.message_counter += 1
                task_msg = IncomingMessage(
                    id=self.message_counter,
                    message_id=event.message_id,
                    sender="RECEIVED-TASK",
                    content=f"📋 RECEIVED-TASK: {title} ({total_steps} steps)",
                    received_at=event.timestamp,
                    is_task=True,
                    is_from_self=False
                )
                self.incoming_messages[event.message_id] = task_msg
                print(f"📋 Received task stored for locking: {event.message_id}")
        except Exception as e:
            print(f"❌ Error storing received task: {e}")

    async def on_task_received(self, event: TaskReceivedEvent):
        """Handle task received events"""
        try:
            if event.message_id in self.incoming_messages:
                return  # Deduplicate
            
            self.message_counter += 1
            msg = IncomingMessage(
                id=self.message_counter,
                message_id=event.message_id,
                sender="SYSTEM",
                content=f"📋 TASK: {event.title} ({event.total_steps} steps)",
                received_at=event.created_at,
                is_task=True
            )
            
            self.incoming_messages[event.message_id] = msg
            
            # Create detailed task info
            task_info = TaskInfo(
                task_id=event.task_id,
                message_id=event.message_id,
                title=event.title,
                total_steps=event.total_steps,
                status=event.status,
                created_by=event.created_by,
                created_at=event.created_at,
                sub_tasks=[]
            )
            
            self.active_tasks[event.task_id] = task_info
            
            print(f"\n📋 NEW TASK #{msg.id}: {event.title}")
            print(f"   Steps: {event.total_steps}")
            print(f"   Created by: {event.created_by}")
            print(f"   Task ID: {event.task_id}")
            print(f"   Message ID: {event.message_id}")
            
            if self.agent_type == "parent":
                print(f"   Use 'lock {msg.id}' to monitor this task")
                print(f"   Use 'tasks' to see real-time progress")
            
            print("\n> ", end="", flush=True)
            
        except Exception as e:
            print(f"❌ Error handling task received: {e}")

    async def handle_task_step_message(self, content_json: dict, event: MessageReceivedEvent):
        """Handle task step messages"""
        try:
            step_number = content_json.get("stepNumber", 0)
            description = content_json.get("description", "Unknown step")
            parent_task_id = content_json.get("parentTaskId", "")
            
            actual_content = f"📝 Step {step_number}: {description}"
            
            # Update parent task tracking
            if parent_task_id in self.active_tasks:
                parent_task = self.active_tasks[parent_task_id]
                existing_step = next((st for st in parent_task.sub_tasks if st.step_number == step_number), None)
                if not existing_step:
                    parent_task.sub_tasks.append(SubTaskInfo(
                        step_number=step_number,
                        description=description,
                        status="pending",
                        message_id=event.message_id
                    ))
                    print(f"\n📝 Task step registered: Step {step_number} for task '{parent_task.title}'")
            
            # Store the step message
            if event.message_id not in self.incoming_messages:
                self.message_counter += 1
                msg = IncomingMessage(
                    id=self.message_counter,
                    message_id=event.message_id,
                    sender="TASK SYSTEM",
                    content=actual_content,
                    received_at=event.timestamp,
                    is_task_step=True,
                    task_id=parent_task_id,
                    step_number=step_number
                )
                
                self.incoming_messages[event.message_id] = msg
                
                print(f"\n🔔 NEW TASK STEP #{msg.id}")
                print(f"   {actual_content}")
                print(f"   Task: {parent_task_id[:8]}...")
                print(f"   Message ID: {msg.message_id}")
                print(f"   Use 'lock {msg.id}' to process this step")
            
            print("\n> ", end="", flush=True)
            
        except Exception as e:
            print(f"❌ Error handling task step: {e}")

    async def handle_task_step_update(self, content_json: dict, event: MessageReceivedEvent):
        """Handle task step update messages"""
        try:
            if event.message_id in self.incoming_messages:
                print(f"⚠️ Skipping duplicate task step update: {event.message_id}")
                return
            
            task_id = content_json.get("parentTaskId", "")
            step_number = content_json.get("stepNumber", 0)
            completed_by = content_json.get("completedBy", "")
            completed_at_str = content_json.get("completedAt", "")
            result = content_json.get("result")
            
            print(f"\n✅ STEP COMPLETED: Step {step_number} by {completed_by}")
            print(f"   Task ID: {task_id}")
            
            # Update task progress
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                print(f"   Found task: {task.title}")
                
                # Find existing subtask or create new one
                sub_task = next((st for st in task.sub_tasks if st.step_number == step_number), None)
                should_increment = False
                
                if sub_task:
                    if sub_task.status != "completed":
                        sub_task.status = "completed"
                        sub_task.completed_by = completed_by
                        should_increment = True
                else:
                    task.sub_tasks.append(SubTaskInfo(
                        step_number=step_number,
                        description=f"Step {step_number}",
                        status="completed",
                        completed_by=completed_by
                    ))
                    should_increment = True
                
                if should_increment:
                    task.completed_steps += 1
                    print(f"   ✅ Task progress updated: {task.completed_steps}/{task.total_steps} steps completed")
                
                if result:
                    print(f"   Result: {result}")
                
                # Send acknowledgment (parent only)
                if self.agent_type == "parent":
                    await self.send_step_acknowledgment(task_id, step_number, completed_by)
                    await self.send_step_removal_request(task_id, step_number)
                
                # FIXED: Check for task completion with synchronization
                if task.completed_steps >= task.total_steps and not task.is_completing:
                    print(f"   🎉 All steps completed! Use 'complete {task_id[:8]}' to finalize task")
                    
                    if self.agent_type == "parent":
                        # Start auto-completion but don't block
                        asyncio.create_task(self.auto_complete_task(task))
            
            print("\n> ", end="", flush=True)
            
        except Exception as e:
            print(f"❌ Error handling task step update: {e}")

    async def send_step_acknowledgment(self, task_id: str, step_number: int, completed_by: str):
        """Send acknowledgment to child agent"""
        try:
            step_message = next((m for m in self.incoming_messages.values() 
                               if m.is_task_step and m.task_id == task_id and m.step_number == step_number), None)
            
            acknowledgment = {
                "type": "step_acknowledged",
                "taskId": task_id,
                "stepNumber": step_number,
                "messageId": step_message.message_id if step_message else "",
                "acknowledgedBy": self.agent_name,
                "acknowledgedAt": datetime.now().isoformat(),
                "originalCompletedBy": completed_by
            }
            
            sent = await self.agent.publish_to_agent(self.pubsub_url, completed_by, json.dumps(acknowledgment))
            if sent:
                print(f"   📤 Acknowledgment sent to {completed_by} for step {step_number}")
            
        except Exception as e:
            print(f"❌ Error sending step acknowledgment: {e}")

    async def send_step_removal_request(self, task_id: str, step_number: int):
        """Send step removal request to all child agents"""
        try:
            removal_request = {
                "type": "step_removal_request",
                "taskId": task_id,
                "stepNumber": step_number,
                "requestedBy": self.agent_name,
                "requestedAt": datetime.now().isoformat()
            }
            
            sent = await self.agent.publish_to_agent(self.pubsub_url, self.agent_name, json.dumps(removal_request))
            if sent:
                print(f"   📤 Step removal request sent for step {step_number}")
                
        except Exception as e:
            print(f"❌ Error sending step removal request: {e}")

    async def handle_step_acknowledgment(self, content_json: dict, event: MessageReceivedEvent):
        """Handle step acknowledgment from parent"""
        try:
            task_id = content_json.get("taskId", "")
            step_number = content_json.get("stepNumber", "")
            acknowledged_message_id = content_json.get("messageId", "")
            
            print(f"\n✅ STEP ACKNOWLEDGED: Step {step_number} for task {task_id[:8]}...")
            
            # Release lock if pending
            if acknowledged_message_id in self.pending_acknowledgments:
                del self.pending_acknowledgments[acknowledged_message_id]
                
                message = next((m for m in self.incoming_messages.values() 
                              if m.message_id == acknowledged_message_id), None)
                if message and message.is_locked:
                    unlocked = await self.agent.release_lock(self.pubsub_url, acknowledged_message_id)
                    if unlocked:
                        message.is_locked = False
                        print(f"✅ Lock released for step {step_number}")
            
            print("\n> ", end="", flush=True)
            
        except Exception as e:
            print(f"❌ Error handling step acknowledgment: {e}")

    async def handle_step_removal_request(self, content_json: dict, event: MessageReceivedEvent):
        """Handle step removal request"""
        try:
            task_id = content_json.get("taskId", "")
            step_number = content_json.get("stepNumber", 0)
            
            print(f"\n🗑️ REMOVING COMPLETED STEP: Step {step_number} from task {task_id[:8]}...")
            
            # Mark step as completed
            step_message = next((m for m in self.incoming_messages.values()
                               if m.is_task_step and m.task_id == task_id and m.step_number == step_number), None)
            
            if step_message:
                step_message.is_completed = True
                print(f"✅ Step {step_number} marked as completed and removed from active list")
            
            print("\n> ", end="", flush=True)
            
        except Exception as e:
            print(f"❌ Error handling step removal: {e}")

    # FIXED: Improved auto-complete task with proper synchronization
    async def auto_complete_task(self, task: TaskInfo):
        """Auto-complete task when all steps are done - with proper synchronization"""
        # Get completion lock for this task
        completion_lock = self.get_task_completion_lock(task.task_id)
        
        async with completion_lock:
            # Check if task is already being completed or completed
            if task.is_completing or task.status == "completed":
                print(f"🔄 Task '{task.title}' is already being completed or completed, skipping auto-completion")
                return
            
            # Mark as completing
            task.is_completing = True
            task.completion_method = "auto"
            
            try:
                await asyncio.sleep(2)  # Wait for final updates
                
                print(f"\n🤖 Auto-completing task '{task.title}'...")
                
                # Find stored message for unlocking
                stored_message = next((m for m in self.incoming_messages.values()
                                     if m.is_from_self and m.is_task and task.task_id in m.message_id), None)
                
                message_id_for_unlock = stored_message.message_id if stored_message else task.message_id
                
                completed = await self.agent.complete_task(self.pubsub_url, task.task_id, message_id_for_unlock)
                
                if completed:
                    task.status = "completed"
                    task.completed_at = datetime.now()
                    print(f"✅ Task '{task.title}' automatically completed and unlocked!")
                    print(f"   All {task.total_steps} steps successfully processed")
                    print(f"   📝 Task is now hidden from active messages. Use 'messages completed' to view.")
                    print(f"   📊 Use 'summary' for quick task overview.")
                else:
                    print(f"❌ Failed to auto-complete task '{task.title}'")
                    print(f"   Use 'complete {task.task_id[:8]}' to complete manually")
                    # Reset completion flag on failure
                    task.is_completing = False
                    task.completion_method = ""
                
                print("\n> ", end="", flush=True)
                
            except Exception as e:
                print(f"❌ Error auto-completing task: {e}")
                # Reset completion flag on error
                task.is_completing = False
                task.completion_method = ""
                print("\n> ", end="", flush=True)

    async def on_task_step_received(self, event: TaskStepEvent):
        """Handle task step received events"""
        try:
            # Store task step message for locking
            if event.message_id not in self.incoming_messages:
                self.message_counter += 1
                step_msg = IncomingMessage(
                    id=self.message_counter,
                    message_id=event.message_id,
                    sender="TASK SYSTEM",
                    content=f"📝 Step {event.step_number}: {event.description}",
                    received_at=datetime.now(),
                    is_task_step=True,
                    task_id=event.parent_task_id,
                    step_number=event.step_number
                )
                
                self.incoming_messages[event.message_id] = step_msg
                
                # Update parent task tracking
                if event.parent_task_id in self.active_tasks:
                    parent_task = self.active_tasks[event.parent_task_id]
                    existing_step = next((st for st in parent_task.sub_tasks if st.step_number == event.step_number), None)
                    if not existing_step:
                        parent_task.sub_tasks.append(SubTaskInfo(
                            step_number=event.step_number,
                            description=event.description,
                            status="pending",
                            message_id=event.message_id
                        ))
                        print(f"\n📝 Task step registered: Step {event.step_number} for task '{parent_task.title}'")
                
                print(f"\n🔔 NEW TASK STEP #{step_msg.id}")
                print(f"   📝 Step {event.step_number}: {event.description}")
                print(f"   Task: {event.parent_task_id[:8]}...")
                print(f"   Message ID: {event.message_id}")
                print(f"   Use 'lock {step_msg.id}' to process this step")
                print("\n> ", end="", flush=True)
                
        except Exception as e:
            print(f"❌ Error handling task step received: {e}")

    async def on_task_step_updated(self, event: TaskStepUpdateEvent):
        """Handle task step updated events"""
        try:
            print(f"\n✅ STEP COMPLETED: Step {event.step_number} by {event.completed_by}")
            print(f"   Task ID: {event.parent_task_id}")
            
            # Update task progress
            if event.parent_task_id in self.active_tasks:
                task = self.active_tasks[event.parent_task_id]
                print(f"   Found task: {task.title}")
                
                # Find existing subtask or create new one
                sub_task = next((st for st in task.sub_tasks if st.step_number == event.step_number), None)
                should_increment = False
                
                if sub_task:
                    if sub_task.status != "completed":
                        sub_task.status = "completed"
                        sub_task.completed_by = event.completed_by
                        sub_task.completed_at = event.completed_at
                        should_increment = True
                else:
                    task.sub_tasks.append(SubTaskInfo(
                        step_number=event.step_number,
                        description=f"Step {event.step_number}",
                        status="completed",
                        completed_by=event.completed_by,
                        completed_at=event.completed_at
                    ))
                    should_increment = True
                
                if should_increment:
                    task.completed_steps += 1
                    print(f"   ✅ Task progress updated: {task.completed_steps}/{task.total_steps} steps completed")
                
                if event.result:
                    print(f"   Result: {event.result}")
                
                # Send acknowledgment (parent only)
                if self.agent_type == "parent":
                    await self.send_step_acknowledgment(event.parent_task_id, event.step_number, event.completed_by)
                    await self.send_step_removal_request(event.parent_task_id, event.step_number)
                
                # FIXED: Check for task completion with synchronization
                if task.completed_steps >= task.total_steps and not task.is_completing:
                    print(f"   🎉 All steps completed! Use 'complete {event.parent_task_id[:8]}' to finalize task")
                    
                    if self.agent_type == "parent":
                        asyncio.create_task(self.auto_complete_task(task))
            
            print("\n> ", end="", flush=True)
            
        except Exception as e:
            print(f"❌ Error handling task step update: {e}")
            print("\n> ", end="", flush=True)

    async def on_task_completed(self, event: TaskCompleteEvent):
        """Handle task completion events"""
        try:
            print(f"\n🎉 TASK COMPLETED: {event.task_id} by {event.completed_by}")
            print(f"   Completed at: {event.completed_at.strftime('%H:%M:%S')}")
            
            if event.task_id in self.active_tasks:
                task = self.active_tasks[event.task_id]
                task.status = "completed"
                task.completed_at = event.completed_at
                # FIXED: Mark as no longer completing
                task.is_completing = False
                print(f"   Final status: All {task.total_steps} steps of '{task.title}' completed")
                
                # Provide helpful guidance
                print(f"   📝 Task and its steps are now hidden from 'messages' (use 'messages completed' to view)")
                print(f"   🧹 Will be auto-cleaned in 5 minutes, or use 'clean' to remove manually")
                print(f"   📊 Use 'summary' for a quick overview of all tasks")
            
            print("\n> ", end="", flush=True)
            
        except Exception as e:
            print(f"❌ Error handling task completion: {e}")

    async def on_lock_expired(self, event: MessageReceivedEvent):
        """Handle lock expiration events"""
        try:
            print(f"\n🔓 LOCK EXPIRED: Message {event.message_id} is now available")
            
            # Update local lock status
            message = next((m for m in self.incoming_messages.values() 
                           if m.message_id == event.message_id), None)
            if message:
                message.is_locked = False
                content_preview = message.content[:30] + "..." if len(message.content) > 30 else message.content
                print(f"   Message #{message.id} ({content_preview}) is now unlocked")
            
            print("\n> ", end="", flush=True)
            
        except Exception as e:
            print(f"❌ Error handling lock expiration: {e}")

    async def connect_with_retry(self) -> bool:
        """Connect to PubSub with retry logic"""
        self.reconnect_attempts = 0
        return await self.attempt_connection()

    async def attempt_connection(self) -> bool:
        """Attempt connection with exponential backoff"""
        while self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                if self.reconnect_attempts > 0:
                    print(f"🔄 Reconnection attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}...")
                else:
                    print("🔄 Connecting to coordination network...")
                
                connected = await self.agent.connect_to_pubsub(self.pubsub_url, self.agent_type)
                
                if connected:
                    print("✅ Connected!")
                    self.reconnect_attempts = 0
                    self.is_reconnecting = False
                    
                    # Start connection monitoring
                    asyncio.create_task(self.monitor_connection())
                    return True
                    
            except Exception as e:
                print(f"❌ Connection failed: {e}")
            
            self.reconnect_attempts += 1
            
            if self.reconnect_attempts < self.max_reconnect_attempts:
                delay = min(60, 2 ** self.reconnect_attempts)
                print(f"⏳ Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
        
        print("❌ Failed to connect after all attempts")
        return False

    async def monitor_connection(self):
        """Monitor connection and auto-reconnect if needed"""
        while self.running:
            await asyncio.sleep(10)  # Check every 10 seconds
            
            if not self.agent.is_connected_to_pubsub() and not self.is_reconnecting:
                self.is_reconnecting = True
                print("\n🔌 Connection lost! Attempting to reconnect...")
                print("> ", end="", flush=True)
                
                # Attempt reconnection in background
                asyncio.create_task(self.handle_reconnection())
                break

    async def handle_reconnection(self):
        """Handle reconnection process"""
        try:
            reconnected = await self.attempt_connection()
            if reconnected:
                print("\n✅ Reconnected successfully!")
            else:
                print("\n❌ Failed to reconnect. Please restart the application.")
            print("> ", end="", flush=True)
        except Exception as e:
            print(f"\n❌ Reconnection error: {e}")
            print("> ", end="", flush=True)

    def show_commands(self):
        """Show available commands"""
        print("\n📋 Available Commands:")
        print("=" * 70)
        
        commands = [
            ("send <agent> <message>", "Send message to specific agent", "send MyAgent Hello there!"),
            ("broadcast <message>", "Send to all agents", "broadcast Hello everyone!"),
            ("schedule <minutes> <message>", "Schedule message for future", "schedule 5 Meeting in 5 mins!"),
            ("messages [active|completed|all]", "Show messages (default: active)", "messages completed"),
            ("summary", "Show task summary overview", "summary"),
            ("clean", "Remove old completed messages", "clean"),
            ("lock <msg#>", "Lock message for processing", "lock 3"),
            ("unlock <msg#>", "Release message lock", "unlock 3"),
        ]
        
        if self.agent_type == "parent":
            commands.extend([
                ("task", "Create interactive task", "task"),
                ("scheduletask <minutes>", "Schedule task creation", "scheduletask 10"),
                ("complete <taskId>", "Complete a task", "complete 6c6cae27"),
                ("taskids", "Show short task IDs", "taskids"),
                ("recover", "Recover existing tasks", "recover"),
            ])
        else:
            commands.append(("complete <msg#>", "Mark step as completed", "complete 3"))
        
        commands.extend([
            ("tasks", "Show detailed task status", "tasks"),
            ("progress", "Show task progress summary", "progress"),
            ("status", "Show agent status", "status"),
            ("pending", "Show pending acknowledgments", "pending"),
            ("clear", "Clear screen", "clear"),
            ("help", "Show this help", "help"),
            ("quit", "Exit demo", "quit"),
        ])
        
        for cmd, desc, example in commands:
            print(f"  {cmd:<30} {desc:<35} {example}")
        
        print("=" * 70)
        
        # Show helpful tips
        print("\n💡 Tips:")
        print("  • 'messages' shows only active tasks by default")
        print("  • 'summary' gives you a quick overview without details")
        print("  • 'clean' removes old completed tasks (5+ minutes old)")
        print("  • Completed tasks are auto-hidden to reduce clutter")

    async def start_interactive_session(self):
        """Start the interactive command session"""
        print(f"\n🎯 Interactive Session Started!")
        print(f"Agent: {self.agent_name} ({self.agent_type})")
        print(f"Connected to: {self.pubsub_url}")
        
        self.show_commands()
        
        # Start event processing in background
        asyncio.create_task(self.agent.start_event_processing())
        
        # Main command loop
        while self.running:
            try:
                command = await asyncio.get_event_loop().run_in_executor(
                    self.executor, input, "\n> "
                )
                
                if not command.strip():
                    continue
                
                parts = command.strip().split()
                cmd = parts[0].lower()
                
                await self.handle_command(cmd, parts)
                
            except (EOFError, KeyboardInterrupt):
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    async def handle_command(self, cmd: str, parts: List[str]):
        """Handle individual commands"""
        try:
            if cmd in ["help", "h"]:
                self.show_commands()
            
            elif cmd == "send":
                await self.handle_send_message(parts)
            
            elif cmd in ["broadcast", "bc"]:
                await self.handle_broadcast(parts)
            
            elif cmd == "schedule":
                await self.handle_schedule(parts)
            
            elif cmd in ["messages", "msg"]:
                # Handle message view options
                view_type = "active"  # default
                if len(parts) > 1:
                    view_type = parts[1].lower()
                    if view_type not in ["active", "completed", "all"]:
                        print("Usage: messages [active|completed|all]")
                        return
                self.show_messages(view_type)
            
            elif cmd == "clean":
                self.clean_completed_messages()
            
            elif cmd == "summary":
                self.show_task_summary()
            
            elif cmd == "lock":
                await self.handle_lock(parts)
            
            elif cmd == "unlock":
                await self.handle_unlock(parts)
            
            elif cmd == "task":
                if self.agent_type == "parent":
                    await self.handle_create_task()
                else:
                    print("Only parent agents can create tasks")
            
            elif cmd == "scheduletask":
                if self.agent_type == "parent":
                    await self.handle_schedule_task(parts)
                else:
                    print("Only parent agents can schedule tasks")
            
            elif cmd == "complete":
                if self.agent_type == "parent":
                    await self.handle_complete_task(parts)
                else:
                    await self.handle_complete_step(parts)
            
            elif cmd == "taskids":
                self.show_task_ids()
            
            elif cmd == "tasks":
                self.show_tasks()
            
            elif cmd == "progress":
                self.show_task_progress()
            
            elif cmd == "status":
                self.show_status()
            
            elif cmd == "pending":
                self.show_pending_acknowledgments()
            
            elif cmd == "clear":
                os.system('clear' if os.name == 'posix' else 'cls')
                self.show_commands()
            
            elif cmd in ["quit", "exit"]:
                await self.exit_demo()
                return
            
            else:
                print("Unknown command. Type 'help' for commands.")
                
        except Exception as e:
            print(f"❌ Error handling command: {e}")

    async def handle_send_message(self, parts: List[str]):
        """Handle send message command"""
        if len(parts) < 3:
            print("Usage: send <agent_name> <message>")
            return
        
        target_agent = parts[1]
        message = " ".join(parts[2:])
        
        print(f"📤 Sending to agent '{target_agent}': {message}")
        
        sent = await self.agent.publish_to_agent(self.pubsub_url, target_agent, message)
        
        if sent:
            self.sent_messages.append(f"To {target_agent}: {message}")
            print("✅ Message sent!")
        else:
            print("❌ Failed to send message")

    async def handle_broadcast(self, parts: List[str]):
        """Handle broadcast message command"""
        if len(parts) < 2:
            print("Usage: broadcast <message>")
            return
        
        message = " ".join(parts[1:])
        
        print(f"📡 Broadcasting: {message}")
        
        sent = await self.agent.publish_broadcast(self.pubsub_url, message)
        
        if sent:
            self.sent_messages.append(f"Broadcast: {message}")
            print("✅ Broadcast sent!")
        else:
            print("❌ Failed to broadcast")

    async def handle_schedule(self, parts: List[str]):
        """Handle schedule message command"""
        if len(parts) < 3:
            print("Usage: schedule <minutes> <message>")
            return
        
        try:
            minutes = int(parts[1])
            if minutes <= 0:
                print("Minutes must be positive")
                return
        except ValueError:
            print("Minutes must be a number")
            return
        
        message = " ".join(parts[2:])
        scheduled_for = datetime.now() + timedelta(minutes=minutes)
        
        print(f"⏰ Scheduling message for {scheduled_for.strftime('%H:%M:%S')} UTC ({minutes} minutes from now)")
        print(f"   Message: {message}")
        
        scheduled = await self.agent.schedule_message(
            self.pubsub_url, scheduled_for, "agent_name", self.agent_name, message
        )
        
        if scheduled:
            print(f"✅ Message scheduled successfully!")
            print(f"   Will be delivered at: {scheduled_for.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        else:
            print("❌ Failed to schedule message")

    async def handle_schedule_task(self, parts: List[str]):
        """FIXED: Handle schedule task command with proper event handling"""
        if len(parts) < 2:
            print("Usage: scheduletask <minutes>")
            return
        
        try:
            minutes = int(parts[1])
            if minutes <= 0:
                print("Minutes must be positive")
                return
        except ValueError:
            print("Minutes must be a number")
            return
        
        scheduled_for = datetime.now() + timedelta(minutes=minutes)
        
        print(f"⏰ Scheduling task creation for {scheduled_for.strftime('%H:%M:%S')} UTC ({minutes} minutes from now)")
        print("Enter task details for scheduling:")
        
        title = await asyncio.get_event_loop().run_in_executor(self.executor, input, "Task title: ")
        description = await asyncio.get_event_loop().run_in_executor(self.executor, input, "Task description: ")
        
        try:
            step_count = int(await asyncio.get_event_loop().run_in_executor(self.executor, input, "Number of steps: "))
        except ValueError:
            print("Invalid step count")
            return
        
        steps = []
        for i in range(1, step_count + 1):
            step_desc = await asyncio.get_event_loop().run_in_executor(self.executor, input, f"Step {i} description: ")
            steps.append(step_desc)
        
        # FIXED: Create task message with predetermined ID for duplicate prevention
        predetermined_task_id = str(uuid.uuid4())
        
        task_message = {
            "type": "scheduled_task_creation",
            "taskId": predetermined_task_id,
            "title": title,
            "description": description,
            "steps": steps,
            "scheduledBy": self.agent_name,
            "scheduledByInternalId": self.agent.get_internal_identity(),
            "originalScheduleTime": datetime.now().isoformat()
        }
        
        print(f"🔧 DEBUG: Scheduling task with internal ID: {self.agent.get_internal_identity()[:8]}...")
        
        scheduled = await self.agent.schedule_message(
            self.pubsub_url, scheduled_for, "agent_name", self.agent_name, 
            json.dumps(task_message), "scheduled_task"
        )
        
        if scheduled:
            print(f"✅ Task scheduled successfully!")
            print(f"   Task '{title}' will be created at: {scheduled_for.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            print(f"   With {step_count} steps")
            print(f"   Predetermined Task ID: {predetermined_task_id}")
            print(f"   The scheduled task creation event will be fired automatically when the time comes")
        else:
            print("❌ Failed to schedule task")

    def show_messages(self, view_type: str = "active"):
        """Show received messages with smart filtering"""
        if not self.incoming_messages:
            print("No messages received yet.")
            return
        
        # Get active locks
        active_locks = self.agent.get_active_locks()
        active_message_ids = {lock.message_id for lock in active_locks}
        
        # Filter messages based on view type
        if view_type == "active":
            messages_to_show = self._get_active_messages()
            title = "📨 Active Messages"
        elif view_type == "completed":
            messages_to_show = self._get_completed_messages()
            title = "✅ Completed Messages"
        else:  # all
            messages_to_show = self._get_all_messages()
            title = "📨 All Messages"
        
        if not messages_to_show:
            if view_type == "active":
                print("🎉 No active messages - all tasks completed!")
                print("Use 'messages completed' to see completed tasks.")
            else:
                print(f"No {view_type} messages found.")
            return
        
        print(f"\n{title}:")
        print("=" * 80)
        print(f"{'#':<3} {'From':<15} {'Content':<40} {'Message ID':<20} {'Time':<8} {'Status':<12}")
        print("-" * 80)
        
        # Sort and show messages
        messages_to_show.sort(key=lambda m: m.id)
        for msg in messages_to_show[-15:]:  # Show more messages
            # Update lock status
            msg.is_locked = msg.message_id in active_message_ids
            
            # Determine status with enhanced indicators
            status = self._get_message_status(msg)
            
            content_preview = msg.content[:37] + "..." if len(msg.content) > 40 else msg.content
            message_id_preview = msg.message_id[:17] + "..." if len(msg.message_id) > 20 else msg.message_id
            
            print(f"{msg.id:<3} {msg.sender:<15} {content_preview:<40} {message_id_preview:<20} "
                  f"{msg.received_at.strftime('%H:%M:%S'):<8} {status:<12}")
        
        print("=" * 80)
        
        # Show helpful tips
        if view_type == "active":
            active_tasks = len([t for t in self.active_tasks.values() if t.status != "completed"])
            completed_tasks = len([t for t in self.active_tasks.values() if t.status == "completed"])
            
            if completed_tasks > 0:
                print(f"💡 Tip: {completed_tasks} completed task(s) hidden. Use 'messages completed' to view them.")
            if active_tasks == 0 and completed_tasks > 0:
                print("🧹 Use 'messages clean' to remove old completed tasks.")

    def _get_active_messages(self):
        """Get only active (non-completed) messages"""
        messages = []
        for msg in self.incoming_messages.values():
            # Skip self-messages except tasks
            if msg.is_from_self and not msg.is_task:
                continue
            
            # For tasks, check if the task is still active
            if msg.is_task:
                if msg.task_id and msg.task_id in self.active_tasks:
                    task = self.active_tasks[msg.task_id]
                    if task.status == "completed":
                        continue  # Skip completed tasks
                elif msg.is_from_self:
                    # For self-tasks, check if any task with this message is completed
                    task_completed = any(t.status == "completed" and msg.message_id in t.message_id 
                                       for t in self.active_tasks.values())
                    if task_completed:
                        continue
            
            # For task steps, check if the parent task is completed or step is completed
            if msg.is_task_step:
                if msg.task_id and msg.task_id in self.active_tasks:
                    task = self.active_tasks[msg.task_id]
                    if task.status == "completed":
                        continue  # Skip steps of completed tasks
                
                # Skip completed steps
                if msg.is_completed:
                    continue
            
            messages.append(msg)
        
        return messages

    def _get_completed_messages(self):
        """Get only completed messages"""
        messages = []
        for msg in self.incoming_messages.values():
            # Skip self-messages except tasks
            if msg.is_from_self and not msg.is_task:
                continue
            
            # For tasks, check if the task is completed
            if msg.is_task:
                if msg.task_id and msg.task_id in self.active_tasks:
                    task = self.active_tasks[msg.task_id]
                    if task.status == "completed":
                        messages.append(msg)
                elif msg.is_from_self:
                    # For self-tasks, check if any task with this message is completed
                    task_completed = any(t.status == "completed" and msg.message_id in t.message_id 
                                       for t in self.active_tasks.values())
                    if task_completed:
                        messages.append(msg)
            
            # For task steps, include if step is completed
            elif msg.is_task_step and msg.is_completed:
                messages.append(msg)
        
        return messages

    def _get_all_messages(self):
        """Get all messages (filter only self-messages except tasks)"""
        return [msg for msg in self.incoming_messages.values() 
                if not msg.is_from_self or msg.is_task]

    def _get_message_status(self, msg):
        """Get enhanced status for a message"""
        # Check if message is in pending acknowledgments
        if msg.message_id in self.pending_acknowledgments:
            return "⏳ PENDING"
        
        # Check if message is locked
        if msg.is_locked:
            return "🔒 LOCKED"
        
        # Check task status
        if msg.is_task:
            if msg.task_id and msg.task_id in self.active_tasks:
                task = self.active_tasks[msg.task_id]
                if task.status == "completed":
                    return "✅ COMPLETED"
                elif task.is_completing:
                    return f"🔄 COMPLETING"
                elif task.completed_steps == task.total_steps:
                    return "⏳ READY"
                else:
                    return f"🔄 ACTIVE ({task.completed_steps}/{task.total_steps})"
            else:
                return "📋 SELF-TASK" if msg.is_from_self else "📋 TASK"
        
        # Check task step status
        if msg.is_task_step:
            if msg.is_completed:
                return "✅ DONE"
            elif msg.task_id and msg.task_id in self.active_tasks:
                task = self.active_tasks[msg.task_id]
                if task.status == "completed":
                    return "✅ DONE"
                sub_task = next((st for st in task.sub_tasks if st.step_number == msg.step_number), None)
                if sub_task:
                    if sub_task.status == "completed":
                        return "✅ DONE"
                    elif sub_task.status == "in_progress":
                        return "🔄 PROCESSING"
                    else:
                        return "⏳ PENDING"
            return "📝 STEP"
        
        # Regular message
        return "💬 Available"

    async def handle_lock(self, parts: List[str]):
        """Handle lock message command"""
        if len(parts) < 2:
            print("Usage: lock <message_number>")
            print("Use 'messages' to see message numbers")
            return
        
        try:
            msg_number = int(parts[1])
        except ValueError:
            print("Message number must be a number")
            return
        
        message = next((m for m in self.incoming_messages.values() if m.id == msg_number), None)
        if not message:
            print(f"Message #{msg_number} not found")
            return
        
        if message.is_locked:
            print(f"Message #{msg_number} is already locked")
            return
        
        # Check if step is already completed
        if message.is_task_step and message.is_completed:
            print(f"❌ Cannot lock message #{msg_number} - this step has already been completed")
            return
        
        print(f"🔒 Attempting to lock message #{msg_number}...")
        
        locked = await self.agent.lock_message(self.pubsub_url, message.message_id)
        
        if locked:
            message.is_locked = True
            print(f"✅ Message #{msg_number} locked successfully!")
            print(f"   Message ID: {message.message_id}")
            
            # Update subtask status if this is a task step
            if message.is_task_step and message.task_id:
                if message.task_id in self.active_tasks:
                    task = self.active_tasks[message.task_id]
                    sub_task = next((st for st in task.sub_tasks if st.step_number == message.step_number), None)
                    if sub_task:
                        sub_task.status = "in_progress"
                        print(f"   Updated step {message.step_number} status to 'in_progress'")
            
            # Process task step if applicable
            if message.is_task_step:
                await self.process_task_step(message)
            else:
                print("Message is now exclusively yours for processing.")
                print(f"Use 'unlock {msg_number}' when done.")
        else:
            print(f"❌ Failed to lock message (another agent may have it)")


    async def process_task_step(self, message: IncomingMessage):
        """Process a task step with simulated work"""
        print(f"🔄 Processing task step {message.step_number}...")
        print(f"   Description: {message.content}")
        print(f"   Task ID: {message.task_id}")
        print("   Simulating work...")

        # Simulate processing with progress
        for i in range(5):
            print(f"   Progress: {'█' * (i+1)}{'░' * (4-i)} {(i+1)*20}%")
            await asyncio.sleep(0.5)

        # FIXED: Create simple result instead of complex nested object
        # This avoids JSON serialization issues and matches C# behavior
        simple_result = f"Step {message.step_number} completed successfully by {self.agent_name}"


        print(f"✅ Processing completed! Updating task status...")
        print(f"   Sending completion notification for step {message.step_number}")


        try:
            # FIXED: Pass simple result string instead of complex object
            update_sent = await self.agent.update_task_step_completion(
        self.pubsub_url, message.task_id, message.step_number, simple_result
            )


            if update_sent:
                print(f"✅ Step completion notification sent successfully")

                # Add to pending acknowledgments - DON'T release lock yet
                self.pending_acknowledgments[message.message_id] = message.task_id


                print(f"⏳ Waiting for parent acknowledgment before releasing lock...")
                print(f"   Result: {simple_result}")
                print(f"   Processing time: 2.5 seconds")
            else:
                print(f"⚠️ Failed to send step completion notification")
                # Release lock immediately if sending failed
                unlocked = await self.agent.release_lock(self.pubsub_url, message.message_id)
                if unlocked:
                    message.is_locked = False
                    print(f"⚠️ Lock released due to communication failure")


        except Exception as e:
            print(f"❌ Error updating task completion: {e}")
            # Try to unlock on error
            try:
                await self.agent.release_lock(self.pubsub_url, message.message_id)
                message.is_locked = False
                print(f"⚠️ Lock released due to error")
            except Exception as unlock_ex:
                print(f"❌ Error unlocking message: {unlock_ex}")

    async def process_task_step2(self, message: IncomingMessage):
        """Process a task step with simulated work"""
        print(f"🔄 Processing task step {message.step_number}...")
        print(f"   Description: {message.content}")
        print(f"   Task ID: {message.task_id}")
        print("   Simulating work...")
        
        # Simulate processing with progress
        for i in range(5):
            print(f"   Progress: {'█' * (i+1)}{'░' * (4-i)} {(i+1)*20}%")
            await asyncio.sleep(0.5)
        
        # Create completion result
        result = {
            "stepNumber": message.step_number,
            "description": message.content,
            "processedBy": self.agent_name,
            "agentInternalId": self.agent.get_internal_identity(),
            "completedAt": datetime.now().isoformat(),
            "result": f"Step {message.step_number} completed successfully by {self.agent_name}",
            "processingTime": "2.5 seconds",
            "taskId": message.task_id,
            "status": "completed",
            "messageId": message.message_id
        }
        
        print(f"✅ Processing completed! Updating task status...")
        print(f"   Sending completion notification for step {message.step_number}")
        
        try:
            # Update completion
            update_sent = await self.agent.update_task_step_completion(
                self.pubsub_url, message.task_id, message.step_number, result
            )
            
            if update_sent:
                print(f"✅ Step completion notification sent successfully")
                
                # Add to pending acknowledgments - DON'T release lock yet
                self.pending_acknowledgments[message.message_id] = message.task_id
                
                print(f"⏳ Waiting for parent acknowledgment before releasing lock...")
                print(f"   Result: {result['result']}")
                print(f"   Processing time: {result['processingTime']}")
            else:
                print(f"⚠️ Failed to send step completion notification")
                # Release lock immediately if sending failed
                unlocked = await self.agent.release_lock(self.pubsub_url, message.message_id)
                if unlocked:
                    message.is_locked = False
                    print(f"⚠️ Lock released due to communication failure")
        
        except Exception as e:
            print(f"❌ Error updating task completion: {e}")
            # Try to unlock on error
            try:
                await self.agent.release_lock(self.pubsub_url, message.message_id)
                message.is_locked = False
                print(f"⚠️ Lock released due to error")
            except Exception as unlock_ex:
                print(f"❌ Error unlocking message: {unlock_ex}")

    async def handle_unlock(self, parts: List[str]):
        """Handle unlock message command"""
        if len(parts) < 2:
            print("Usage: unlock <message_number>")
            return
        
        try:
            msg_number = int(parts[1])
        except ValueError:
            print("Message number must be a number")
            return
        
        message = next((m for m in self.incoming_messages.values() if m.id == msg_number), None)
        if not message:
            print(f"Message #{msg_number} not found")
            return
        
        if not message.is_locked:
            print(f"Message #{msg_number} is not locked")
            return
        
        print(f"🔓 Releasing lock on message #{msg_number}...")
        
        unlocked = await self.agent.release_lock(self.pubsub_url, message.message_id)
        
        if unlocked:
            message.is_locked = False
            print(f"✅ Message #{msg_number} unlocked!")
        else:
            print("❌ Failed to unlock message")

    async def handle_create_task(self):
        """Handle create task command"""
        print("\n📋 Creating Interactive Task")
        print("Enter task details:")
        
        title = await asyncio.get_event_loop().run_in_executor(self.executor, input, "Task title: ")
        description = await asyncio.get_event_loop().run_in_executor(self.executor, input, "Task description: ")
        
        try:
            step_count = int(await asyncio.get_event_loop().run_in_executor(self.executor, input, "Number of steps: "))
        except ValueError:
            print("Invalid step count")
            return
        
        steps = []
        for i in range(1, step_count + 1):
            step_desc = await asyncio.get_event_loop().run_in_executor(self.executor, input, f"Step {i} description: ")
            steps.append(step_desc)
        
        print(f"\n🔄 Creating task '{title}' with {step_count} steps...")
        
        try:
            result = await self.agent.create_and_lock_task(self.pubsub_url, title, description, steps)
            
            if result:
                task_id, message_id = result
                
                # Wait for message to be processed
                await asyncio.sleep(1)
                
                # Find stored task message for locking
                stored_message = next((m for m in self.incoming_messages.values()
                                     if m.is_from_self and m.is_task and task_id in m.message_id), None)
                
                actual_message_id = message_id
                is_actually_locked = False
                
                if stored_message:
                    locked = await self.agent.lock_message(self.pubsub_url, stored_message.message_id)
                    if locked:
                        actual_message_id = stored_message.message_id
                        is_actually_locked = True
                        print(f"✅ Task created and locked for monitoring!")
                    else:
                        print(f"✅ Task created but locking failed!")
                else:
                    print(f"✅ Task created but message not found for locking!")
                
                print(f"Task ID: {task_id}")
                print(f"Message ID: {actual_message_id}")
                print(f"Locked: {'Yes' if is_actually_locked else 'No'}")
                print(f"Steps will be sent to child agents for processing...")
                
                self.active_tasks[task_id] = TaskInfo(
                    task_id=task_id,
                    message_id=actual_message_id,
                    title=title,
                    total_steps=step_count,
                    status="in_progress",
                    created_by=self.agent_name,
                    created_at=datetime.now(),
                    sub_tasks=[]
                )
                
                print("✅ Task tracking initialized locally")
            else:
                print("❌ Failed to create task")
                
        except Exception as e:
            print(f"❌ Error creating task: {e}")

    # FIXED: Improved handle_complete_task with proper synchronization
    async def handle_complete_task(self, parts: List[str]):
        """Handle complete task command (parent agents) - FIXED with synchronization"""
        if len(parts) < 2:
            print("Usage: complete <taskId>")
            print("Use 'taskids' to see short task IDs")
            return
        
        partial_task_id = parts[1]
        
        # Find task by partial ID
        matching_tasks = [t for t in self.active_tasks.values() 
                         if t.task_id.startswith(partial_task_id) or partial_task_id in t.task_id]
        
        if not matching_tasks:
            print(f"No task found matching '{partial_task_id}'")
            print("Use 'taskids' to see available task IDs")
            return
        
        if len(matching_tasks) > 1:
            print(f"Multiple tasks match '{partial_task_id}':")
            for t in matching_tasks:
                print(f"  {t.task_id[:12]}... - {t.title}")
            print("Please be more specific.")
            return
        
        task = matching_tasks[0]
        
        # FIXED: Check if task is already completed or being completed
        if task.status == "completed":
            print(f"Task '{task.title}' is already completed!")
            return
        
        if task.is_completing:
            print(f"Task '{task.title}' is already being completed by {task.completion_method} completion.")
            print("Please wait for the completion process to finish.")
            return
        
        if task.completed_steps < task.total_steps:
            print(f"Cannot complete task - only {task.completed_steps}/{task.total_steps} steps completed")
            print("Wait for all child agents to complete their steps.")
            return
        
        # Get completion lock for this task
        completion_lock = self.get_task_completion_lock(task.task_id)
        
        async with completion_lock:
            # Double-check status inside the lock
            if task.is_completing or task.status == "completed":
                print(f"Task '{task.title}' is already being completed or completed.")
                return
            
            # Mark as completing
            task.is_completing = True
            task.completion_method = "manual"
            
            print(f"🔄 Completing task '{task.title}'...")
            print(f"  All {task.total_steps} steps have been completed")
            
            try:
                # Find stored message for unlocking
                stored_message = next((m for m in self.incoming_messages.values()
                                     if m.is_from_self and m.is_task and task.task_id in m.message_id), None)
                
                message_id_for_unlock = stored_message.message_id if stored_message else task.message_id
                
                print(f"🔧 DEBUG: Using message ID for unlock: {message_id_for_unlock[:20]}...")
                
                completed = await self.agent.complete_task(self.pubsub_url, task.task_id, message_id_for_unlock)
                
                if completed:
                    task.status = "completed"
                    task.completed_at = datetime.now()
                    print(f"✅ Task '{task.title}' marked as completed and unlocked!")
                    print(f"   All {task.total_steps} steps successfully processed")
                    print(f"   Completion time: {task.completed_at.strftime('%H:%M:%S')}")
                else:
                    print("❌ Failed to complete task")
                    # Reset completion flag on failure
                    task.is_completing = False
                    task.completion_method = ""
                    
            except Exception as e:
                print(f"❌ Error completing task: {e}")
                # Reset completion flag on error
                task.is_completing = False
                task.completion_method = ""

    async def handle_complete_step(self, parts: List[str]):
        """Handle complete step command (child agents)"""
        if len(parts) < 2:
            print("Usage: complete <message_number>")
            print("Use 'messages' to see message numbers")
            return
        
        try:
            msg_number = int(parts[1])
        except ValueError:
            print("Message number must be a number")
            return
        
        message = next((m for m in self.incoming_messages.values() if m.id == msg_number), None)
        if not message:
            print(f"Message #{msg_number} not found")
            return
        
        if not message.is_task_step:
            print(f"Message #{msg_number} is not a task step")
            return
        
        if not message.is_locked:
            print(f"Message #{msg_number} is not locked - lock it first")
            return
        
        if message.is_completed:
            print(f"Message #{msg_number} has already been completed")
            return
        
        print(f"✅ Marking step {message.step_number} as completed...")

        try:
            # FIXED: Create simple result instead of complex object
            simple_result = f"Step {message.step_number} completed by {self.agent_name}"

            # Send completion notification with simple result
            update_sent = await self.agent.update_task_step_completion(
                self.pubsub_url, message.task_id, message.step_number, simple_result
            )

            # Send completion notification
            update_sent = await self.agent.update_task_step_completion(
                self.pubsub_url, message.task_id, message.step_number, result
            )
            
            if update_sent:
                print(f"✅ Step {message.step_number} marked as completed")
                
                # Add to pending acknowledgments
                self.pending_acknowledgments[message.message_id] = message.task_id
                
                print(f"⏳ Waiting for parent acknowledgment before releasing lock...")
                
                # Update local subtask status
                if message.task_id in self.active_tasks:
                    task = self.active_tasks[message.task_id]
                    sub_task = next((st for st in task.sub_tasks if st.step_number == message.step_number), None)
                    if sub_task:
                        sub_task.status = "completed"
                        sub_task.completed_by = self.agent_name
                        sub_task.completed_at = datetime.now()
            else:
                print(f"❌ Failed to mark step as completed")
                # Release lock on failure
                unlocked = await self.agent.release_lock(self.pubsub_url, message.message_id)
                if unlocked:
                    message.is_locked = False
                    print(f"⚠️ Lock released due to communication failure")
        
        except Exception as e:
            print(f"❌ Error completing step: {e}")
            # Try to unlock on error
            try:
                await self.agent.release_lock(self.pubsub_url, message.message_id)
                message.is_locked = False
                print(f"⚠️ Lock released due to error")
            except Exception as unlock_ex:
                print(f"❌ Error unlocking message: {unlock_ex}")

    def clean_completed_messages(self):
        """Remove completed tasks and steps from messages"""
        if not self.incoming_messages:
            print("No messages to clean.")
            return
        
        initial_count = len(self.incoming_messages)
        
        # Find messages to remove (completed tasks and their steps)
        messages_to_remove = []
        
        for msg_id, msg in self.incoming_messages.items():
            should_remove = False
            
            # Remove completed tasks
            if msg.is_task:
                if msg.task_id and msg.task_id in self.active_tasks:
                    task = self.active_tasks[msg.task_id]
                    if task.status == "completed":
                        # Only remove if completed more than 5 minutes ago
                        if task.completed_at and (datetime.now() - task.completed_at).total_seconds() > 300:
                            should_remove = True
                elif msg.is_from_self:
                    # For self-tasks, check if any task with this message is completed
                    for task in self.active_tasks.values():
                        if (task.status == "completed" and msg.message_id in task.message_id and 
                            task.completed_at and (datetime.now() - task.completed_at).total_seconds() > 300):
                            should_remove = True
                            break
            
            # Remove completed task steps
            elif msg.is_task_step:
                if msg.task_id and msg.task_id in self.active_tasks:
                    task = self.active_tasks[msg.task_id]
                    if task.status == "completed":
                        if task.completed_at and (datetime.now() - task.completed_at).total_seconds() > 300:
                            should_remove = True
                elif msg.is_completed:
                    # Remove steps completed more than 5 minutes ago
                    if (datetime.now() - msg.received_at).total_seconds() > 300:
                        should_remove = True
            
            if should_remove:
                messages_to_remove.append(msg_id)
        
        # Remove the messages
        for msg_id in messages_to_remove:
            del self.incoming_messages[msg_id]
        
        removed_count = len(messages_to_remove)
        
        if removed_count > 0:
            print(f"🧹 Cleaned {removed_count} completed messages (older than 5 minutes)")
            print(f"📊 Messages: {initial_count} → {len(self.incoming_messages)}")
        else:
            print("✨ No old completed messages to clean")
            print("💡 Messages are auto-cleaned 5 minutes after task completion")

    def show_task_summary(self):
        """Show a concise summary of all tasks"""
        if not self.active_tasks:
            print("📋 No tasks found.")
            return
        
        print("\n📊 Task Summary:")
        print("=" * 70)
        
        # Categorize tasks
        active_tasks = [t for t in self.active_tasks.values() if t.status != "completed"]
        completed_tasks = [t for t in self.active_tasks.values() if t.status == "completed"]
        
        # Show statistics
        total_tasks = len(self.active_tasks)
        total_steps = sum(t.total_steps for t in self.active_tasks.values())
        completed_steps = sum(t.completed_steps for t in self.active_tasks.values())
        
        print(f"📈 Overview: {total_tasks} tasks, {completed_steps}/{total_steps} steps completed")
        print(f"🔄 Active: {len(active_tasks)} tasks")
        print(f"✅ Completed: {len(completed_tasks)} tasks")
        
        if active_tasks:
            print(f"\n🔄 Active Tasks:")
            print(f"{'ID':<10} {'Title':<25} {'Progress':<12} {'Status':<15}")
            print("-" * 65)
            
            for task in sorted(active_tasks, key=lambda t: t.created_at):
                progress = f"{task.completed_steps}/{task.total_steps}"
                status = "🔄 Completing" if task.is_completing else "⏳ Ready" if task.completed_steps == task.total_steps else "🔄 Active"
                
                print(f"{task.task_id[:8]:<10} {task.title[:24]:<25} {progress:<12} {status:<15}")
        
        if completed_tasks:
            print(f"\n✅ Recently Completed Tasks:")
            print(f"{'ID':<10} {'Title':<25} {'Completed':<12} {'Duration':<15}")
            print("-" * 65)
            
            for task in sorted(completed_tasks, key=lambda t: t.completed_at or t.created_at, reverse=True)[:5]:
                completed_time = task.completed_at.strftime('%H:%M:%S') if task.completed_at else "Unknown"
                duration = ""
                if task.completed_at:
                    duration = str(task.completed_at - task.created_at).split('.')[0]  # Remove microseconds
                
                print(f"{task.task_id[:8]:<10} {task.title[:24]:<25} {completed_time:<12} {duration:<15}")
        
        print("=" * 70)
        
        # Show quick tips
        if active_tasks:
            ready_tasks = [t for t in active_tasks if t.completed_steps == t.total_steps and not t.is_completing]
            if ready_tasks:
                print(f"💡 {len(ready_tasks)} task(s) ready for completion. Use 'complete <taskId>' to finalize.")
        
        if len(completed_tasks) > 5:
            print(f"💡 Use 'messages completed' to see all {len(completed_tasks)} completed tasks.")
        
        if completed_tasks:
            old_completed = [t for t in completed_tasks if t.completed_at and 
                           (datetime.now() - t.completed_at).total_seconds() > 300]
            if old_completed:
                print(f"🧹 Use 'clean' to remove {len(old_completed)} old completed tasks.")

    def show_task_ids(self):
        """Show task IDs for completion"""
        if not self.active_tasks:
            print("No active tasks.")
            return
        
        print("📋 Task IDs for completion:")
        for task in self.active_tasks.values():
            short_id = task.task_id[:8]
            # FIXED: Show completion status
            if task.status == "completed":
                status_icon = "✅"
            elif task.is_completing:
                status_icon = f"🔄({task.completion_method})"
            elif task.completed_steps == task.total_steps:
                status_icon = "⏳"
            else:
                status_icon = "🔄"
            
            print(f"  {short_id} - {status_icon} {task.title} ({task.completed_steps}/{task.total_steps})")
        
        print("\nUse: complete <shortId>  (e.g., complete 6c6cae27)")

    def show_task_ids(self):
        """Show task IDs for completion"""
        if not self.active_tasks:
            print("No active tasks.")
            return
        
        print("📋 Task IDs for completion:")
        for task in self.active_tasks.values():
            short_id = task.task_id[:8]
            # FIXED: Show completion status
            if task.status == "completed":
                status_icon = "✅"
            elif task.is_completing:
                status_icon = f"🔄({task.completion_method})"
            elif task.completed_steps == task.total_steps:
                status_icon = "⏳"
            else:
                status_icon = "🔄"
            
            print(f"  {short_id} - {status_icon} {task.title} ({task.completed_steps}/{task.total_steps})")
        
        print("\nUse: complete <shortId>  (e.g., complete 6c6cae27)")

    def show_task_progress(self):
        """Show task progress summary"""
        if not self.active_tasks:
            print("No active tasks.")
            return
        
        print("📊 Task Progress Summary:")
        for task in sorted(self.active_tasks.values(), key=lambda t: t.created_at, reverse=True):
            # FIXED: Show completion status
            if task.status == "completed":
                status_icon = "✅"
            elif task.is_completing:
                status_icon = f"🔄({task.completion_method})"
            elif task.completed_steps == task.total_steps:
                status_icon = "⏳"
            else:
                status_icon = "🔄"
                
            progress_percent = (task.completed_steps / task.total_steps * 100) if task.total_steps > 0 else 0
            
            print(f"\n{status_icon} {task.title}")
            print(f"   Progress: {task.completed_steps}/{task.total_steps} ({progress_percent:.1f}%)")
            print(f"   Status: {task.status}")
            if task.is_completing:
                print(f"   Completion Method: {task.completion_method}")
            print(f"   Created: {task.created_at.strftime('%H:%M:%S')} by {task.created_by}")
            
            if task.completed_at:
                print(f"   Completed: {task.completed_at.strftime('%H:%M:%S')}")
            
            if task.sub_tasks:
                pending = len([st for st in task.sub_tasks if st.status == "pending"])
                in_progress = len([st for st in task.sub_tasks if st.status == "in_progress"])
                completed = len([st for st in task.sub_tasks if st.status == "completed"])
                
                print(f"   Steps: {completed} completed, {in_progress} in progress, {pending} pending")

    def show_tasks(self):
        """Show detailed task status"""
        if not self.active_tasks:
            print("No active tasks.")
            return
        
        for task in self.active_tasks.values():
            print(f"\n📋 Task: {task.title}")
            print("=" * 60)
            print(f"Task ID: {task.task_id[:12]}...")
            print(f"Progress: {task.completed_steps}/{task.total_steps} steps")
            
            status_color = "completed" if task.status == "completed" else "pending" if task.completed_steps == task.total_steps else "in_progress"
            print(f"Status: {task.status} ({status_color})")
            # FIXED: Show completion info
            if task.is_completing:
                print(f"Completion Method: {task.completion_method}")
            print(f"Created By: {task.created_by}")
            print(f"Created At: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if task.completed_at:
                print(f"Completed At: {task.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Show subtasks
            if task.sub_tasks:
                print("\n📝 Sub-Tasks:")
                print(f"{'Step':<6} {'Description':<40} {'Status':<12} {'Completed By':<15} {'Completed At':<12}")
                print("-" * 90)
                
                for sub_task in sorted(task.sub_tasks, key=lambda st: st.step_number):
                    status = "✅ Completed" if sub_task.status == "completed" else "🔄 Processing" if sub_task.status == "in_progress" else "⏳ Pending"
                    description = sub_task.description[:37] + "..." if len(sub_task.description) > 40 else sub_task.description
                    completed_by = sub_task.completed_by or "-"
                    completed_at = sub_task.completed_at.strftime('%H:%M:%S') if sub_task.completed_at else "-"
                    
                    print(f"{sub_task.step_number:<6} {description:<40} {status:<12} {completed_by:<15} {completed_at:<12}")
            else:
                if self.agent_type == "parent":
                    print("   (No subtask details available yet - they'll appear as child agents process them)")

    def show_status(self):
        """Show agent status"""
        print("\n🔍 Agent Status:")
        print("=" * 40)
        print(f"Agent Name: {self.agent_name}")
        print(f"Agent Type: {self.agent_type}")
        print(f"Internal ID: {self.agent.get_internal_identity()[:20]}...")
        print(f"Connected: {'✅ Yes' if self.agent.is_connected_to_pubsub() else '❌ No'}")
        print(f"Messages Received: {len(self.incoming_messages)}")
        print(f"Messages Sent: {len(self.sent_messages)}")
        print(f"Active Tasks: {len(self.active_tasks)}")
        print(f"Completed Tasks: {len([t for t in self.active_tasks.values() if t.status == 'completed'])}")
        # FIXED: Show completing tasks
        print(f"Completing Tasks: {len([t for t in self.active_tasks.values() if t.is_completing])}")
        print(f"Active Locks: {len(self.agent.get_active_locks())}")
        print(f"Pending Acknowledgments: {len(self.pending_acknowledgments)}")
        print(f"Reconnect Attempts: {self.reconnect_attempts}")

    def show_pending_acknowledgments(self):
        """Show pending acknowledgments"""
        if not self.pending_acknowledgments:
            print("No pending acknowledgments.")
            return
        
        print("⏳ Pending Acknowledgments:")
        for message_id, task_id in self.pending_acknowledgments.items():
            message = next((m for m in self.incoming_messages.values() if m.message_id == message_id), None)
            if message:
                print(f"   Message #{message.id}: Step {message.step_number} of task {task_id[:8]}...")
                print(f"   Message ID: {message_id[:20]}...")
            else:
                print(f"   Message ID: {message_id[:20]}... (message not found)")

    async def exit_demo(self):
        """Exit the demo gracefully"""
        print("👋 Disconnecting...")
        self.running = False
        
        if self.agent:
            self.agent.stop_event_processing()
            self.agent.disconnect_from_pubsub()
            self.agent.dispose()
        
        await asyncio.sleep(1)
        print("Goodbye!")

    async def run_demo(self, args):
        """Run the complete demo"""
        try:
            self.show_welcome()
            
            # Get configuration
            config = self.get_agent_config(args)
            if not config:
                return
            
            self.agent_type = config.agent_type
            self.pubsub_url = config.pubsub_url
            
            # Initialize agent
            if not await self.initialize_agent(config):
                return
            
            # Setup event handlers
            self.setup_event_handlers()
            
            # Connect with retry
            if not await self.connect_with_retry():
                return
            
            # Start interactive session
            await self.start_interactive_session()
            
        except KeyboardInterrupt:
            print("\n👋 Interrupted by user")
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await self.exit_demo()

# ==================================================================================
# MAIN ENTRY POINT
# ==================================================================================

async def main():
    """Main entry point"""
    # Setup signal handling
    def signal_handler(signum, frame):
        print("\n👋 Received interrupt signal...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='HexaEight Interactive Agent Demo')
    parser.add_argument('config_file', nargs='?', help='Agent configuration file')
    parser.add_argument('agent_type', nargs='?', choices=['parent', 'child'], help='Agent type')
    args = parser.parse_args()
    
    # Create and run demo
    demo = HexaEightAgentDemo()
    await demo.run_demo(sys.argv)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
