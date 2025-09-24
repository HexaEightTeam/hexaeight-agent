#!/usr/bin/env python3
"""
DLL Integrity Verification Test

Tests the DLL JWT verification using the new is_file_path parameter.
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

async def test_dll_jwt_verification():
    """Test DLL JWT verification using file paths."""
    print("=" * 80)
    print("  DLL JWT Verification Test")
    print("=" * 80)

    agent = HexaEightAgent(debug_mode=True)
    agent.set_signing_folder(SIGNING_FOLDER)
    agent.start_signing_queue()

    try:
        # Test with HexaEightAgent.dll
        dll_path = os.path.join(DLL_DIR, "HexaEightAgent.dll")
        jwt_path = os.path.join(SIGNING_FOLDER, "HexaEightAgent.dll.jwt")

        print(f"\n📁 DLL Path: {dll_path}")
        print(f"🔐 JWT Path: {jwt_path}")

        if not os.path.exists(dll_path):
            print(f"❌ DLL not found: {dll_path}")
            return False

        if not os.path.exists(jwt_path):
            print(f"⚠️  JWT file not found: {jwt_path}")
            print(f"🔐 Creating JWT for DLL...")

            # Create JWT from the DLL file
            request_id = await agent.queue_signing_from_file_async("support@hexaeight.com", dll_path)
            if not request_id:
                print(f"❌ Failed to queue signing: no request ID returned")
                return False

            wait_result = await agent.wait_for_queue_result_async(request_id)
            if not wait_result["success"]:
                print(f"❌ Failed to create JWT: {wait_result.get('error')}")
                return False

            jwt_content = wait_result["jwt"]

            # Save the JWT file
            with open(jwt_path, 'w') as f:
                f.write(jwt_content)
            print(f"✅ Created and saved JWT: {jwt_path}")
        else:
            # Read the JWT content
            with open(jwt_path, 'r') as f:
                jwt_content = f.read().strip()

        print(f"✅ JWT loaded, length: {len(jwt_content)} chars")

        # Test verification with is_file_path=True
        print(f"\n🔍 Verifying DLL integrity using file path...")
        verify_result = await agent.verify_jwt_async(
            jwt_content,
            dll_path,
            "support@hexaeight.com",
            is_file_path=True
        )

        if verify_result["success"] and verify_result["verified"]:
            print(f"✅ DLL verification successful!")
            print(f"⏱️  Verification time: {verify_result['verification_time_ms']}ms")
            print(f"👤 Sender hash: {verify_result['sender_hash'][:64] if verify_result['sender_hash'] else 'N/A'}...")
            print(f"✍️  Signed by: {verify_result['signed_by']}")
            return True
        else:
            print(f"❌ DLL verification failed: {verify_result.get('error')}")
            return False

    finally:
        await agent.stop_signing_queue_async()

if __name__ == "__main__":
    try:
        result = asyncio.run(test_dll_jwt_verification())
        if result:
            print("\n🎉 DLL JWT verification PASSED!")
            sys.exit(0)
        else:
            print("\n❌ DLL JWT verification FAILED!")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)