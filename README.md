# HexaEight Agent - Python Library

A Python wrapper for HexaEight Agent that enables secure multi-agent communication and coordination for AI systems.

## What is HexaEight Agent?

HexaEight Agent provides identity management and secure communication for AI agents. This library allows agents built with any framework (CrewAI, LangChain, AutoGen, etc.) to:

1. 🔐 **Authenticate** with unique identities
2. 💬 **Communicate securely** with end-to-end encryption
3. 📋 **Coordinate tasks** across multiple agents
4. 🔒 **Lock messages** for exclusive processing
5. ⏰ **Schedule messages** and tasks
6. 🌐 **Bridge communication** across agents
7. 📤 **Publish messages** with direct, broadcast, and scheduled delivery
8. ⚡ **Handle events** with real-time processing and async iteration

## Requirements

- Python 3.8 or higher
- .NET 8.0 Runtime
- Access to Agentic IAM (HexaEight Token Server and PubSub Server)
- HexaEight credentials (Client ID, Resource Name, Machine Token)

## Installation

```bash
pip install hexaeight-agent
```

## Quick Start

1. **Install HexaEight Licensed Machine Token** on a host machine (Visit: https://store.hexaeight.com)

2. **Setup an Agentic IAM Server** - Configure HexaEight Token Server + HexaEight PubSub Server

3. **Create an Application** and get a Client ID

4. **Create Parent Agent** using the licensed host machine:
   ```bash
   dotnet script create-identity-for-parent-agent.csx parent_config.json --no-cache
   ```

5. **Create Child Agents** using the parent agent configuration:
   ```bash
   dotnet script create-identity-for-child-agent.csx child_01 parent_config.json --no-cache
   ```

6. **Test Parent Agent** from licensed host machine using demo:
   ```bash
   python3 hexaeight_demo.py parent_config.json parent 
   ```

7. **Test Child Agent** from any machine using the configuration files:
   ```bash
   python3 hexaeight_demo.py config_agent02.json child
   ```

8. **Establish Secure Communication** across agents by sending messages, locking messages, creating tasks, etc.

> **Note**: A Licensed machine token is required for creating parent and child agents. The parent and child agents are created as JSON configuration files. Once created, these agents remain active forever, even after the machine token expires.

## Agent Types

**Parent Agents**: Can create and manage tasks, tied to the licensed host machine, have full administrative capabilities, and can coordinate multiple child agents.

**Child Agents**: Can run on any machine, created using parent agent configuration, can participate in tasks and communication, and inherit security from parent agent.

## Usage Examples

Refer to `hexaeight_demo.py` for complete examples of all features.

## License

Apache License 2.0 - See [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: Coming Soon
- **Contact**: support@hexaeight.com

---

*HexaEight Agent - Enabling secure, scalable AI agent communication*
