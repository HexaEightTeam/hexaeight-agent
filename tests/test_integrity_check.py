#!/usr/bin/env python3
"""
Test DLL integrity verification during package initialization
"""

import sys
import os

# Change to signing folder first (required for env-file loading)
SIGNING_FOLDER = "/home/ubuntu/signature-license"
os.chdir(SIGNING_FOLDER)

# Add local hexaeight-agent package to path
sys.path.insert(0, "/home/ubuntu/hexaeight-agent")

def test_package_initialization():
    """Test if the package loads successfully with DLL integrity verification."""
    print("=" * 80)
    print("  Testing HexaEightAgent Package Initialization with DLL Integrity")
    print("=" * 80)

    try:
        print("🔍 Importing HexaEightAgent package...")
        from hexaeight_agent import HexaEightAgent

        print("✅ Package imported successfully!")
        print("✅ DLL integrity verification passed!")

        # Test basic functionality
        print("\n🧪 Testing basic functionality...")
        agent = HexaEightAgent(debug_mode=False)
        print("✅ Agent instance created successfully!")

        return True

    except Exception as e:
        print(f"❌ Package initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = test_package_initialization()
    if result:
        print("\n🎉 SUCCESS: Package loads with DLL integrity verification!")
        sys.exit(0)
    else:
        print("\n❌ FAILED: Package initialization failed!")
        sys.exit(1)