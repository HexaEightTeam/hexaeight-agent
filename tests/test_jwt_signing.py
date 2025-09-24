#!/usr/bin/env python3
"""
HexaEight JWT Signing Integration Test

Tests the Python-to-C# DLL integration for JWT signing and verification.
Uses HexaEightAgent.dll 1.6.860 with advanced queuing capabilities.
"""

import asyncio
import sys
import os
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from hexaeight_agent import HexaEightAgent

# Test configuration
SIGNING_FOLDER = "/home/ubuntu/signature-license"

# Change to signing folder (required for env-file loading)
os.chdir(SIGNING_FOLDER)
TEST_EMAIL = "test@example.com"
TEST_MESSAGE = "Hello World! This is a test message for Python JWT signing."


def print_separator(title: str = ""):
    """Print a separator line with optional title."""
    if title:
        print(f"\n{'=' * 80}")
        print(f"  {title}")
        print(f"{'=' * 80}")
    else:
        print(f"{'=' * 80}")


async def test_basic_signing():
    """Test 1: Basic JWT signing and verification."""
    print_separator("TEST 1: Basic JWT Signing & Verification")

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
            print(f"✅ Verification successful!")
            print(f"⏱️  Verification time: {verify_result['verification_time_ms']}ms")
            print(f"👤 Sender hash: {verify_result['sender_hash'][:64]}...")
            print(f"✍️  Signed by: {verify_result['signed_by']}")
            return True
        else:
            print(f"❌ Verification failed: {verify_result.get('error')}")
            return False
    else:
        print(f"❌ Signing failed: {sign_result.get('error')}")
        return False


async def test_jwt_message_json():
    """Test 2: Complete JWT message JSON creation and verification."""
    print_separator("TEST 2: Complete JWT Message JSON")

    agent = HexaEightAgent(debug_mode=True)
    agent.set_signing_folder(SIGNING_FOLDER)

    user_email = "user@example.com"
    important_message = "Important authenticated message with complete JSON structure"

    print(f"\n📦 Creating JWT message JSON for: {user_email}")
    print(f"📄 Message: {important_message}")

    # Create complete JWT message JSON
    create_result = await agent.create_jwt_message_async(user_email, important_message)

    if create_result["success"]:
        print(f"\n✅ JWT message created!")
        print(f"📏 JSON length: {len(create_result['jwt_message_json'])} chars")
        print(f"🆔 Message ID: {create_result['msg_id']}")

        # Verify the JWT message JSON
        print(f"\n🔍 Verifying JWT message JSON...")
        verify_result = await agent.verify_jwt_message_async(
            create_result["jwt_message_json"],
            user_email
        )

        if verify_result["success"]:
            print(f"✅ JWT message verification successful!")
            print(f"⏱️  Verification time: {verify_result['verification_time_ms']}ms")
            print(f"👤 Sender hash: {verify_result['sender_hash'][:64]}...")
            print(f"✍️  Signed by: {verify_result['signed_by']}")
            return True
        else:
            print(f"❌ Verification failed: {verify_result.get('error')}")
            return False
    else:
        print(f"❌ JWT message creation failed: {create_result.get('error')}")
        return False


async def test_verification_without_signing_env():
    """Test 3: JWT verification WITHOUT signing environment."""
    print_separator("TEST 3: JWT Verification Without Signing Environment")

    # First, create a signed JWT with signing environment
    agent_with_env = HexaEightAgent(debug_mode=False)
    agent_with_env.set_signing_folder(SIGNING_FOLDER)

    test_msg = "Verification test message"
    test_email = "verify@example.com"

    print(f"\n📝 Creating test JWT with signing environment...")
    sign_result = await agent_with_env.sign_message_async(test_email, test_msg)

    if not sign_result["success"]:
        print(f"❌ Failed to create test JWT: {sign_result.get('error')}")
        return False

    test_jwt = sign_result["jwt"]
    print(f"✅ Test JWT created (length: {len(test_jwt)} chars)")

    # Now verify WITHOUT signing environment
    print(f"\n🔓 Creating verifier WITHOUT signing environment...")
    verifier_only = HexaEightAgent(debug_mode=True)  # No set_signing_folder!

    print(f"🔍 Attempting verification without signing credentials...")
    verify_result = await verifier_only.verify_jwt_async(test_jwt, test_msg, test_email)

    if verify_result["success"] and verify_result["verified"]:
        print(f"✅ Verification WITHOUT signing environment: SUCCESS!")
        print(f"⏱️  Verification time: {verify_result['verification_time_ms']}ms")
        print(f"👤 Verified sender hash: {verify_result['sender_hash'][:64]}...")
        print(f"✍️  Signed by: {verify_result['signed_by']}")
        print(f"\n🎯 JWT verification is independent of signing credentials!")
        return True
    else:
        print(f"❌ Verification failed: {verify_result.get('error')}")
        return False


async def test_queue_based_signing():
    """Test 4: Queue-based async signing."""
    print_separator("TEST 4: Queue-Based Async Signing")

    agent = HexaEightAgent(debug_mode=True)
    agent.set_signing_folder(SIGNING_FOLDER)

    print("\n🚀 Starting JWT signing queue system...")
    agent.start_signing_queue()

    # Queue multiple signing requests
    print(f"\n📤 Queuing 3 concurrent signing requests...")
    request_ids = []

    for i in range(1, 4):
        msg = f"Concurrent message #{i} - timestamp: {time.time()}"
        req_id = await agent.queue_signing_async(f"user{i}@test.com", msg)
        request_ids.append(req_id)
        print(f"   ✓ Queued request {i}: {req_id}")

    print(f"\n⏳ Waiting for all requests to complete...")

    results = []
    for req_id in request_ids:
        result = await agent.wait_for_queue_result_async(req_id, timeout_ms=10000)
        results.append(result)

        if result["success"]:
            print(f"   ✅ Request {req_id[:8]}... completed in {result['generation_time_ms']}ms")
        else:
            print(f"   ❌ Request {req_id[:8]}... failed: {result.get('error')}")

    # Get queue statistics
    print(f"\n📊 Queue Statistics:")
    stats = agent.get_queue_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Stop queue
    await agent.stop_signing_queue_async()

    success_count = sum(1 for r in results if r["success"])
    return success_count == len(results)


async def run_all_tests():
    """Run all integration tests."""
    print("\n" + "=" * 80)
    print("  HexaEight JWT Signing - Python DLL Integration Test Suite")
    print("  Using HexaEightAgent.dll 1.6.860 with Advanced Queuing")
    print("=" * 80)

    tests = [
        ("Basic Signing & Verification", test_basic_signing),
        ("Complete JWT Message JSON", test_jwt_message_json),
        ("Verification Without Signing Env", test_verification_without_signing_env),
        ("Queue-Based Signing", test_queue_based_signing),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Print summary
    print_separator("TEST RESULTS SUMMARY")
    print()

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")

    total_tests = len(results)
    passed_tests = sum(1 for _, result in results if result)

    print()
    print(f"  Total: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("\n🎉 All tests PASSED! Python-to-C# DLL integration is working perfectly!")
        print("🚀 HexaEightAgent JWT signing is PRODUCTION READY for Python!")
        return 0
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed. Review the output above.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(run_all_tests())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)