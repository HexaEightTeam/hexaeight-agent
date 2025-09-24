#!/usr/bin/env python3
"""Test 1: Basic JWT Signing & Verification"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from hexaeight_agent import HexaEightAgent

SIGNING_FOLDER = "/home/ubuntu/signature-license"
TEST_EMAIL = "test@example.com"
TEST_MESSAGE = "Hello World! This is a test message for Python JWT signing."

async def test_basic_signing():
    # Change to signing folder directory (required for env-file loading)
    os.chdir(SIGNING_FOLDER)
    print("\n" + "="*80)
    print("  TEST 1: Basic JWT Signing & Verification")
    print("="*80)

    print("\n📝 Initializing HexaEight Agent...")
    agent = HexaEightAgent(debug_mode=True)
    agent.set_signing_folder(SIGNING_FOLDER)

    print(f"\n🔏 Signing message from: {TEST_EMAIL}")
    print(f"📄 Message: {TEST_MESSAGE}")

    # Sign the message
    sign_result = await agent.sign_message_async(TEST_EMAIL, TEST_MESSAGE)

    if sign_result["success"]:
        print(f"\n✅ Signing successful!")
        print(f"⏱️  Generation time: {sign_result['generation_time_ms']}ms")
        print(f"🆔 Message ID: {sign_result['message_id']}")
        print(f"📏 JWT length: {len(sign_result['jwt'])} chars")
        print(f"🔐 JWT preview: {sign_result['jwt'][:100]}...")

        # Verify the signed message
        print(f"\n🔍 Verifying JWT signature...")
        verify_result = await agent.verify_jwt_async(
            sign_result['jwt'],
            TEST_MESSAGE,
            TEST_EMAIL
        )

        if verify_result["success"] and verify_result["verified"]:
            print(f"\n✅ Verification successful!")
            print(f"⏱️  Verification time: {verify_result['verification_time_ms']}ms")
            print(f"👤 Sender hash: {verify_result['sender_hash'][:64]}...")
            print(f"✍️  Signed by: {verify_result['signed_by']}")
            print(f"\n🎉 TEST 1 PASSED!")
            return 0
        else:
            print(f"\n❌ Verification failed: {verify_result.get('error')}")
            return 1
    else:
        print(f"\n❌ Signing failed: {sign_result.get('error')}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(test_basic_signing())
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)