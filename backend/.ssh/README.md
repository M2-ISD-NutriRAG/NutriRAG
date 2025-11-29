# Snowflake Key Pair Authentication Setup

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

```bash
pip install -r backend/requirements.txt
```

### Step 4: Test the Connection

Run your script again:

```bash
# From your project root directory (e.g., /path/to/NutriRAG)
cd backend
python -m data.embeddings.create_table
```

## How It Works

The `SnowflakeClient` class now:

1. Checks for `SNOWFLAKE_PRIVATE_KEY_PATH` environment variable
2. If found, loads the private key and uses key pair authentication
3. If not found, falls back to password authentication
4. Includes `ocsp_fail_open=True` to handle certificate validation issues

## Troubleshooting

### "Permission denied" error

Ensure the private key file has appropriate permissions:

```bash
chmod 600 backend/.ssh/rsa_key.p8
```

### "Public key not found" error

Make sure you've added the public key to your Snowflake user account using the SQL command above.

### Still getting MFA errors

Verify that:

1. The public key was added correctly (no extra spaces or line breaks)
2. You're using the correct username in the ALTER USER command
3. Your Snowflake admin hasn't restricted key pair authentication

## Regenerating Keys

If you need to regenerate the keys:

```bash
# Generate new private key
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out backend/.ssh/rsa_key.p8 -nocrypt

# Generate new public key
openssl rsa -in backend/.ssh/rsa_key.p8 -pubout -out backend/.ssh/rsa_key.pub

# View the public key content (for adding to Snowflake)
cat backend/.ssh/rsa_key.pub
```

Then repeat Step 1 with the new public key.
