#!/usr/bin/env python3
"""
Create JWT files for all critical DLLs and deploy them to the package directory

This script:
1. Creates JWTs for all 3 critical DLLs (HexaEightAgent, HexaEightJWTLibrary, HexaEightASKClientLibrary)
2. Copies the JWT files to the hexaeight_agent package directory
3. Verifies the deployment worked correctly

Usage:
    cd /home/ubuntu/signature-license
    source /home/ubuntu/agent/workdir/agent_env/bin/activate
    python3 /home/ubuntu/hexaeight-agent/tests/create_and_deploy_dll_jwts.py
"""

import asyncio
import sys
import os
import shutil
from pathlib import Path

# Change to signing folder first (required for env-file loading)
SIGNING_FOLDER = "/home/ubuntu/signature-license"
os.chdir(SIGNING_FOLDER)

# Add local hexaeight-agent package to path
sys.path.insert(0, "/home/ubuntu/hexaeight-agent")

from hexaeight_agent import HexaEightAgent

# Configuration
DLL_DIR = "/home/ubuntu/hexaeight-agent/hexaeight_agent/dlls"
PACKAGE_DIR = "/home/ubuntu/hexaeight-agent/hexaeight_agent"
CRITICAL_DLLS = [
    "HexaEightAgent.dll",
    "HexaEightJWTLibrary.dll",
    "HexaEightASKClientLibrary.dll"
]

async def create_and_deploy_dll_jwts():
    """Create JWT files for all critical DLLs and deploy them."""
    print("=" * 80)
    print("  Creating and Deploying DLL JWT Files")
    print("=" * 80)
    print(f"📁 DLL Directory: {DLL_DIR}")
    print(f"📦 Package Directory: {PACKAGE_DIR}")
    print(f"🔐 Signing Folder: {SIGNING_FOLDER}")

    # Initialize agent for JWT creation
    agent = HexaEightAgent(debug_mode=True)
    agent.set_signing_folder(SIGNING_FOLDER)
    agent.start_signing_queue()

    try:
        created_jwts = []

        # Step 1: Create JWTs for all critical DLLs
        print(f"\n📝 Step 1: Creating JWTs for {len(CRITICAL_DLLS)} critical DLLs...")

        for dll_name in CRITICAL_DLLS:
            dll_path = os.path.join(DLL_DIR, dll_name)
            temp_jwt_path = os.path.join(SIGNING_FOLDER, f"{dll_name}.jwt")

            print(f"\n🔐 Creating JWT for {dll_name}...")

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

            # Save JWT to temporary location
            with open(temp_jwt_path, 'w') as f:
                f.write(jwt_content)

            created_jwts.append((dll_name, temp_jwt_path, len(jwt_content)))
            print(f"   ✅ Created JWT: {len(jwt_content)} chars")

        # Step 2: Deploy JWTs to package directory
        print(f"\n📦 Step 2: Deploying {len(created_jwts)} JWTs to package directory...")

        deployed_jwts = []
        for dll_name, temp_jwt_path, jwt_size in created_jwts:
            target_jwt_path = os.path.join(PACKAGE_DIR, f"{dll_name}.jwt")

            try:
                shutil.copy2(temp_jwt_path, target_jwt_path)
                deployed_jwts.append((dll_name, target_jwt_path, jwt_size))
                print(f"   ✅ Deployed {dll_name}.jwt -> {target_jwt_path}")
            except Exception as e:
                print(f"   ❌ Failed to deploy {dll_name}.jwt: {e}")

        # Step 3: Verify deployment
        print(f"\n🔍 Step 3: Verifying deployment...")

        all_verified = True
        for dll_name, target_jwt_path, expected_size in deployed_jwts:
            if os.path.exists(target_jwt_path):
                actual_size = os.path.getsize(target_jwt_path)
                if actual_size == expected_size:
                    print(f"   ✅ {dll_name}.jwt verified: {actual_size} bytes")
                else:
                    print(f"   ❌ {dll_name}.jwt size mismatch: expected {expected_size}, got {actual_size}")
                    all_verified = False
            else:
                print(f"   ❌ {dll_name}.jwt not found at {target_jwt_path}")
                all_verified = False

        # Summary
        print(f"\n{'=' * 80}")
        if all_verified and len(deployed_jwts) == len(CRITICAL_DLLS):
            print("🎉 SUCCESS: All DLL JWT files created and deployed successfully!")
            print(f"   Created JWTs: {len(created_jwts)}/{len(CRITICAL_DLLS)}")
            print(f"   Deployed JWTs: {len(deployed_jwts)}/{len(CRITICAL_DLLS)}")
            print(f"   Verification: ✅ All verified")
            print("\n📋 Deployed files:")
            for dll_name, target_path, size in deployed_jwts:
                print(f"   • {target_path} ({size} bytes)")
            return True
        else:
            print("❌ FAILED: Deployment incomplete or verification failed!")
            return False

    finally:
        await agent.stop_signing_queue_async()

if __name__ == "__main__":
    print("🚀 DLL JWT Creation and Deployment Tool")
    print("   This tool creates signed JWTs for critical DLLs and deploys them to the package.")

    try:
        result = asyncio.run(create_and_deploy_dll_jwts())
        if result:
            print("\n✨ Ready! The hexaeight-agent package now has DLL integrity protection.")
            sys.exit(0)
        else:
            print("\n💥 Failed! Check the output above for errors.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)