#!/usr/bin/env python3
"""
Create JWT files for all critical DLLs
"""

import asyncio
import sys
import os
from pathlib import Path

# Change to signing folder first (required for env-file loading)
SIGNING_FOLDER = "/home/ubuntu/signature-license"
os.chdir(SIGNING_FOLDER)

# Add local hexaeight-agent package to path
sys.path.insert(0, "/home/ubuntu/hexaeight-agent")

from hexaeight_agent import HexaEightAgent

# Test configuration
DLL_DIR = "/home/ubuntu/hexaeight-agent/hexaeight_agent/dlls"
CRITICAL_DLLS = [
    "HexaEightAgent.dll",
    "HexaEightJWTLibrary.dll",
    "HexaEightASKClientLibrary.dll"
]

async def create_all_dll_jwts():
    """Create JWT files for all critical DLLs."""
    print("=" * 80)
    print("  Creating JWT files for all critical DLLs")
    print("=" * 80)

    agent = HexaEightAgent(debug_mode=True)
    agent.set_signing_folder(SIGNING_FOLDER)
    agent.start_signing_queue()

    try:
        for dll_name in CRITICAL_DLLS:
            dll_path = os.path.join(DLL_DIR, dll_name)
            jwt_path = os.path.join(SIGNING_FOLDER, f"{dll_name}.jwt")

            print(f"\n🔐 Creating JWT for {dll_name}...")
            print(f"   DLL: {dll_path}")
            print(f"   JWT: {jwt_path}")

            if not os.path.exists(dll_path):
                print(f"   ❌ DLL not found: {dll_path}")
                continue

            # Create JWT from the DLL file
            request_id = await agent.queue_signing_from_file_async("support@hexaeight.com", dll_path)
            if not request_id:
                print(f"   ❌ Failed to queue signing: no request ID returned")
                continue

            wait_result = await agent.wait_for_queue_result_async(request_id)
            if not wait_result["success"]:
                print(f"   ❌ Failed to create JWT: {wait_result.get('error')}")
                continue

            jwt_content = wait_result["jwt"]

            # Save the JWT file
            with open(jwt_path, 'w') as f:
                f.write(jwt_content)
            print(f"   ✅ Created JWT: {len(jwt_content)} chars")

        print(f"\n🎉 All DLL JWT files created successfully!")
        return True

    finally:
        await agent.stop_signing_queue_async()

if __name__ == "__main__":
    try:
        result = asyncio.run(create_all_dll_jwts())
        if result:
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)