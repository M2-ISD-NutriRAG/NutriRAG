# Snowflake Key Pair Authentication Setup

<<<<<<< HEAD
This guide walks you through setting up secure key pair authentication for Snowflake, eliminating the need for password/MFA prompts.

## Overview

**What is this?** This directory contains RSA key pairs used to authenticate with Snowflake without passwords.

**Why use it?** Key pair authentication is ideal for automated scripts and bypasses MFA requirements while maintaining security.

**What you'll do:**

1. Generate RSA keys
2. Configure Snowflake to accept your public key
3. Configure your application to use the private key
4. Test the connection

---

## ⚠️ Security First

- **NEVER commit `rsa_key.p8` (private key) to version control**
- `.gitignore` is already configured to protect your private key
- Keep `rsa_key.p8` secure and never share it
- Only the public key (`rsa_key.pub`) should be shared with Snowflake

---

## Complete Setup Guide

### Step 1: Generate Your RSA Key Pair

Run these commands from your project root directory:

```bash
# Generate the private key (2048-bit RSA in PKCS#8 format)
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out backend/.ssh/rsa_key.p8 -nocrypt

# Generate the public key from the private key
openssl rsa -in backend/.ssh/rsa_key.p8 -pubout -out backend/.ssh/rsa_key.pub
```

**Files created:**

- `rsa_key.p8` - Your private key (🔒 KEEP SECRET)
- `rsa_key.pub` - Your public key (safe to share)

**Set appropriate permissions (Linux/Mac):**

```bash
chmod 600 backend/.ssh/rsa_key.p8
```

---

### Step 2: Extract the Public Key Content

You need to get the public key content WITHOUT the header/footer lines.

**Option A: View and copy manually**

```bash
cat backend/.ssh/rsa_key.pub
```

Copy everything EXCEPT these lines:

- `-----BEGIN PUBLIC KEY-----`
- `-----END PUBLIC KEY-----`

**Option B: Extract directly (Linux/Mac)**

```bash
grep -v "BEGIN PUBLIC KEY" backend/.ssh/rsa_key.pub | grep -v "END PUBLIC KEY" | tr -d '\n'
```

---

### Step 3: Add Public Key to Snowflake

1. **Log in to Snowflake** (web UI or SQL client with password/MFA)

2. **Run this SQL command** (replace `YOUR_USERNAME` with your actual Snowflake username):

```sql
ALTER USER YOUR_USERNAME SET RSA_PUBLIC_KEY='<paste_public_key_content_here>';
```

**Example:**

```sql
ALTER USER JOHN_DOE SET RSA_PUBLIC_KEY='MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...';
```

**Important:** Paste only the base64 content, NOT the BEGIN/END lines!

3. **Verify it was added** (optional):

```sql
DESCRIBE USER YOUR_USERNAME;
```

Look for the `RSA_PUBLIC_KEY_FP` property - it should show a fingerprint value.

---

### Step 4: Install Required Dependencies

Ensure the `cryptography` library is installed:
=======
This directory contains the RSA key pair used for authenticating with Snowflake.

## ⚠️ IMPORTANT SECURITY NOTES

- **NEVER commit private keys to version control**
- The `.gitignore` file is configured to exclude private key files in this directory
- Keep your private key (`rsa_key.p8`) secure and never share it
- Only share the public key (`rsa_key.pub`) with Snowflake administrators

## Files Generated

- `rsa_key.p8` - Private key (KEEP SECRET)
- `rsa_key.pub` - Public key (safe to share with Snowflake)

## Setup Instructions

### Step 1: Add Public Key to Your Snowflake User

You need to configure your Snowflake user account to accept key pair authentication.

1. Log in to Snowflake (using the web UI or a client with password/MFA)
2. Execute the following SQL command (replace `YOUR_USERNAME` with your actual Snowflake username):

```sql
ALTER USER YOUR_USERNAME SET RSA_PUBLIC_KEY='<public_key_string>';
```

**Note:** The public key string above does NOT include the `-----BEGIN PUBLIC KEY-----` and `-----END PUBLIC KEY-----` headers/footers. Only the base64-encoded content is used.

### Step 2: Configure Environment Variables

Add the snowflake private key path to your `.env` file. The path can be relative or absolute:

```bash
# Key pair authentication (recommended for MFA accounts)
SNOWFLAKE_PRIVATE_KEY_PATH=/absolute/path/to/your/project/backend/.ssh/rsa_key.p8

# Or use an absolute path for reliability (recommended):
# SNOWFLAKE_PRIVATE_KEY_PATH=/absolute/path/to/your/project/backend/.ssh/rsa_key.p8
```

**Note:** The relative path is resolved from your current working directory when running the script. If you run your script from different locations, consider using an absolute path for reliability.

> You can comment out the password line.

### Step 3: Install Dependencies

Ensure you have the cryptography library installed:
>>>>>>> 555951e (fix: better architecture for create embeddings table)

```bash
pip install -r backend/requirements.txt
```

<<<<<<< HEAD
---

### Step 5: Configure Environment Variables

Add the private key path to your `.env` file at the project root:

**Option A: Relative path** (simpler, but working directory dependent)

```bash
SNOWFLAKE_PRIVATE_KEY_PATH=backend/.ssh/rsa_key.p8
```

**Option B: Absolute path** (recommended for reliability)

```bash
SNOWFLAKE_PRIVATE_KEY_PATH=path_to_your_project/backend/.ssh/rsa_key.p8
```

**Optional:** Comment out the password line if you have one:

```bash
# SNOWFLAKE_PASSWORD=your_old_password
```

---

### Step 6: Test Your Connection

Run a test script from the backend directory:

```bash
=======
### Step 4: Test the Connection

Run your script again:

```bash
# From your project root directory (e.g., /path/to/NutriRAG)
>>>>>>> 555951e (fix: better architecture for create embeddings table)
cd backend
python -m data.embeddings.create_table
```

<<<<<<< HEAD
**Success indicators:**

- ✅ No MFA prompt
- ✅ Connection established
- ✅ Script runs without authentication errors

---

## How It Works

The `SnowflakeClient` automatically:

1. Checks for `SNOWFLAKE_PRIVATE_KEY_PATH` environment variable
2. If found → loads private key → uses key pair authentication
3. If not found → falls back to password authentication
4. Includes `ocsp_fail_open=True` for certificate validation handling

---

## Troubleshooting

### Problem: "Permission denied" when reading private key

**Solution:** Ensure correct file permissions (Linux/Mac)
=======
## How It Works

The `SnowflakeClient` class now:

1. Checks for `SNOWFLAKE_PRIVATE_KEY_PATH` environment variable
2. If found, loads the private key and uses key pair authentication
3. If not found, falls back to password authentication
4. Includes `ocsp_fail_open=True` to handle certificate validation issues

## Troubleshooting

### "Permission denied" error

Ensure the private key file has appropriate permissions:
>>>>>>> 555951e (fix: better architecture for create embeddings table)

```bash
chmod 600 backend/.ssh/rsa_key.p8
```

<<<<<<< HEAD
### Problem: "JWT token is invalid" or "Public key not found"

**Possible causes:**

- Public key not added to Snowflake user account
- Wrong username used in ALTER USER command
- Extra spaces/line breaks in the public key string
- Public key includes BEGIN/END lines (it shouldn't!)

**Solution:** Re-run the ALTER USER command with the correct public key content.

### Problem: Still getting MFA prompts

**Check these:**

1. ✅ Environment variable is set correctly in `.env`
2. ✅ Private key path is correct (try absolute path)
3. ✅ `.env` file is loaded by your application
4. ✅ Username matches the user with the public key

### Problem: "Could not deserialize key data" or cryptography errors

**Solution:** Ensure the private key is in PKCS#8 format and regenerate if needed:

```bash
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out backend/.ssh/rsa_key.p8 -nocrypt
```

### Problem: Connection works locally but fails in Docker

**Solution:** Ensure the private key is accessible in the Docker container:

- Mount the `.ssh` directory as a volume, OR
- Copy the key during Docker build (not recommended for production), OR
- Use Docker secrets for production environments

---

## Regenerating Keys

If you need to generate new keys (e.g., key compromised or expired):
=======
### "Public key not found" error

Make sure you've added the public key to your Snowflake user account using the SQL command above.

### Still getting MFA errors

Verify that:

1. The public key was added correctly (no extra spaces or line breaks)
2. You're using the correct username in the ALTER USER command
3. Your Snowflake admin hasn't restricted key pair authentication

## Regenerating Keys

If you need to regenerate the keys:
>>>>>>> 555951e (fix: better architecture for create embeddings table)

```bash
# Generate new private key
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out backend/.ssh/rsa_key.p8 -nocrypt

# Generate new public key
openssl rsa -in backend/.ssh/rsa_key.p8 -pubout -out backend/.ssh/rsa_key.pub

<<<<<<< HEAD
# View public key content
cat backend/.ssh/rsa_key.pub
```

**Then:** Return to [Step 3](#step-3-add-public-key-to-snowflake) and update Snowflake with the new public key.

---

## Additional Resources

- [Snowflake Key Pair Authentication Documentation](https://docs.snowflake.com/en/user-guide/key-pair-auth.html)
- [OpenSSL Documentation](https://www.openssl.org/docs/)

---

## Quick Reference

**Key files:**

- `rsa_key.p8` → Private key (keep secret)
- `rsa_key.pub` → Public key (add to Snowflake)

**Environment variable:**

```bash
SNOWFLAKE_PRIVATE_KEY_PATH=backend/.ssh/rsa_key.p8
```

**Snowflake SQL:**

```sql
ALTER USER YOUR_USERNAME SET RSA_PUBLIC_KEY='<public_key_content>';
```
=======
# View the public key content (for adding to Snowflake)
cat backend/.ssh/rsa_key.pub
```

Then repeat Step 1 with the new public key.
>>>>>>> 555951e (fix: better architecture for create embeddings table)
