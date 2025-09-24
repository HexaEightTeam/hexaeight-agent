# DLL Integrity Verification

This package includes built-in DLL integrity verification to prevent tampering with the HexaEight .NET assemblies.

## Verified DLLs

The following DLLs are verified on package import:

### HexaEightAgent.dll
- **Version:** 1.6.860.0
- **SHA256:** `ce55af3b952537c1ebedf4b8c77c9bd429d0cbf67a14de737ba8038c4eeee0ed`
- **Purpose:** Core agent functionality and JWT signing

### HexaEightJWTLibrary.dll
- **Version:** 1.9.268.0
- **SHA256:** `15d5080ecfa6dbdb7bae432e658d0b877ea62a4308f15929f1aa6ce31c03bfc0`
- **Purpose:** JWT token generation and verification

### HexaEightASKClientLibrary.dll
- **Version:** 1.9.103.0
- **SHA256:** `5ad9a76f51e31b38e05da23cbe50345d1c47f2208839b0775c0352a8ee583521`
- **Purpose:** HexaEight ASK client functionality

## How It Works

1. **Hash Verification:** On package import, each DLL's SHA256 hash is computed and compared against the expected hash
2. **Version Verification:** After loading, each DLL's assembly version is verified to match the expected version
3. **Security Error:** If any verification fails, a `SecurityError` is raised preventing the package from loading

## Security Notice

If you receive a DLL integrity verification error:
- **DO NOT** ignore the error
- **DO NOT** attempt to bypass the verification
- Reinstall the package from the official PyPI repository: `pip install --force-reinstall hexaeight-agent`
- Report any persistent issues to the package maintainers

## Verifying Manually

You can manually verify the DLLs using:

```bash
# SHA256 hashes
cd hexaeight_agent/dlls
sha256sum HexaEightAgent.dll HexaEightJWTLibrary.dll HexaEightASKClientLibrary.dll
```

Compare the output with the hashes listed above.