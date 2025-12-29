#!/usr/bin/env python3
"""
Snowflake Key Pair Authentication Setup Script

This script automates the setup of RSA key pair authentication for Snowflake,
guiding users through each step with confirmations for critical operations.

IMPORTANT: Run this script with the virtual environment activated:
    source ../venv/bin/activate  # From backend directory
    python setup_snowflake.py

Or use the venv Python directly:
    ../venv/bin/python setup_snowflake.py
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


class Colors:
    """ANSI color codes for terminal output."""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


class SnowflakeSetup:
    """Handles Snowflake key pair authentication setup."""

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize the setup handler.

        Args:
            project_root: Path to project root. Defaults to parent of backend directory.
        """
        # Script is in backend/, so project root is parent directory
        backend_dir = Path(__file__).parent
        self.project_root = project_root or backend_dir.parent
        self.ssh_dir = backend_dir / ".ssh"
        self.private_key_path = self.ssh_dir / "rsa_key.p8"
        self.public_key_path = self.ssh_dir / "rsa_key.pub"
        self.env_file = self.project_root / ".env"
        self.requirements_file = backend_dir / "requirements.txt"

    def print_header(self, message: str) -> None:
        """Print a formatted header message."""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{message}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}\n")

    def print_success(self, message: str) -> None:
        """Print a success message."""
        print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")

    def print_warning(self, message: str) -> None:
        """Print a warning message."""
        print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")

    def print_error(self, message: str) -> None:
        """Print an error message."""
        print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")

    def print_info(self, message: str) -> None:
        """Print an info message."""
        print(f"{Colors.OKCYAN}ℹ {message}{Colors.ENDC}")

    def confirm_action(self, message: str, default: bool = False) -> bool:
        """
        Ask user for confirmation.

        Args:
            message: Question to ask the user
            default: Default response if user just presses Enter

        Returns:
            True if user confirms, False otherwise
        """
        suffix = " [Y/n]: " if default else " [y/N]: "
        while True:
            response = (
                input(f"{Colors.BOLD}{message}{suffix}{Colors.ENDC}")
                .strip()
                .lower()
            )
            if not response:
                return default
            if response in ["y", "yes"]:
                return True
            if response in ["n", "no"]:
                return False
            print("Please answer 'y' or 'n'")

    def setup_keys(self) -> bool:
        """
        Generate RSA key pair for Snowflake authentication.

        Returns:
            True if keys were generated successfully, False otherwise
        """
        self.print_header("Step 1: Generate RSA Key Pair")

        # Check if keys already exist
        if self.private_key_path.exists() or self.public_key_path.exists():
            self.print_warning("Keys already exist!")
            if self.private_key_path.exists():
                print(f"  - Private key: {self.private_key_path}")
            if self.public_key_path.exists():
                print(f"  - Public key: {self.public_key_path}")

            if not self.confirm_action(
                "Do you want to regenerate the keys? (This will overwrite existing keys)"
            ):
                self.print_info("Skipping key generation. Using existing keys.")
                return True

        # Ensure .ssh directory exists
        self.ssh_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Generate private key
            self.print_info(
                "Generating private key (2048-bit RSA in PKCS#8 format)..."
            )
            genrsa = subprocess.run(
                ["openssl", "genrsa", "2048"],
                capture_output=True,
                check=True,
                text=True,
            )

            subprocess.run(
                [
                    "openssl",
                    "pkcs8",
                    "-topk8",
                    "-inform",
                    "PEM",
                    "-out",
                    str(self.private_key_path),
                    "-nocrypt",
                ],
                input=genrsa.stdout,
                capture_output=True,
                check=True,
                text=True,
            )

            # Generate public key
            self.print_info("Generating public key from private key...")
            subprocess.run(
                [
                    "openssl",
                    "rsa",
                    "-in",
                    str(self.private_key_path),
                    "-pubout",
                    "-out",
                    str(self.public_key_path),
                ],
                capture_output=True,
                check=True,
            )

            # Set appropriate permissions (Unix-like systems)
            if os.name != "nt":  # Not Windows
                os.chmod(self.private_key_path, 0o600)
                self.print_success("Set private key permissions to 600")

            self.print_success(f"Private key created: {self.private_key_path}")
            self.print_success(f"Public key created: {self.public_key_path}")
            return True

        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to generate keys: {e}")
            if e.stderr:
                print(f"Error details: {e.stderr}")
            return False
        except Exception as e:
            self.print_error(f"Unexpected error: {e}")
            return False

    def extract_public_key(self) -> Optional[str]:
        """
        Extract public key content without header/footer.

        Returns:
            Public key content as a single string, or None if extraction fails
        """
        self.print_header("Step 2: Extract Public Key Content")

        if not self.public_key_path.exists():
            self.print_error(f"Public key not found at {self.public_key_path}")
            return None

        try:
            with open(self.public_key_path, "r") as f:
                lines = f.readlines()

            # Remove header, footer, and newlines
            public_key_content = "".join(
                line.strip() for line in lines if not line.startswith("-----")
            )

            self.print_success("Public key extracted successfully!")
            print(
                f"\n{Colors.BOLD}Public Key Content (first 80 chars):{Colors.ENDC}"
            )
            print(f"{Colors.OKCYAN}{public_key_content[:80]}...{Colors.ENDC}")

            return public_key_content

        except Exception as e:
            self.print_error(f"Failed to extract public key: {e}")
            return None

    def configure_snowflake(self, public_key_content: str) -> bool:
        """
        Guide user to configure Snowflake with the public key.

        Args:
            public_key_content: The extracted public key content

        Returns:
            True if user confirms configuration is complete, False otherwise
        """
        self.print_header("Step 3: Add Public Key to Snowflake")

        print(
            "You need to add the public key to your Snowflake user account.\n"
        )
        print(f"{Colors.BOLD}Instructions:{Colors.ENDC}")
        print("1. Log in to Snowflake (web UI or SQL client)")
        print("2. Run the following SQL command:\n")

        username = input(
            f"{Colors.BOLD}Enter your Snowflake username: {Colors.ENDC}"
        ).strip()

        sql_command = (
            f"ALTER USER {username} SET RSA_PUBLIC_KEY='{public_key_content}';"
        )

        print(f"\n{Colors.OKBLUE}{Colors.BOLD}SQL Command to run:{Colors.ENDC}")
        print(f"{Colors.OKBLUE}{sql_command}{Colors.ENDC}\n")

        # Copy to clipboard if possible (optional)
        try:
            import pyperclip

            pyperclip.copy(sql_command)
            self.print_success("SQL command copied to clipboard!")
        except ImportError:
            self.print_info(
                "Tip: Install 'pyperclip' to auto-copy the SQL command: pip install pyperclip"
            )

        print(f"\n{Colors.BOLD}Verification (optional):{Colors.ENDC}")
        print(f"DESCRIBE USER {username};\n")
        print(
            "Look for the 'RSA_PUBLIC_KEY_FP' property with a fingerprint value.\n"
        )

        if not self.confirm_action(
            "Have you successfully added the public key to Snowflake?"
        ):
            self.print_warning(
                "Please add the public key to Snowflake before continuing."
            )
            return False

        self.print_success("Snowflake configuration confirmed!")
        return True

    def check_dependencies(self) -> bool:
        """
        Check if required Python dependencies are installed.

        Returns:
            True if dependencies are installed or user chooses to continue, False otherwise
        """
        self.print_header("Step 4: Check Dependencies")

        # Mapping of pip package names to Python import names
        required_packages = {
            "snowflake-connector-python": "snowflake.connector",
            "cryptography": "cryptography",
            "python-dotenv": "dotenv",
        }
        missing_packages = []

        for package_name, import_name in required_packages.items():
            try:
                __import__(import_name)
                self.print_success(f"{package_name} is installed")
            except ImportError:
                missing_packages.append(package_name)
                self.print_warning(f"{package_name} is NOT installed")

        if missing_packages:
            print(
                f"\n{Colors.WARNING}Missing packages: {', '.join(missing_packages)}{Colors.ENDC}\n"
            )

            if self.confirm_action(
                "Do you want to install missing dependencies now?", default=True
            ):
                return self.install_dependencies()
            else:
                self.print_info("You can install dependencies later using:")
                self.print_info(f"  pip install -r {self.requirements_file}")
                return self.confirm_action("Continue anyway?")
        else:
            self.print_success("All required dependencies are installed!")
            return True

    def install_dependencies(self) -> bool:
        """
        Install Python dependencies from requirements.txt.

        Returns:
            True if installation succeeds, False otherwise
        """
        if not self.requirements_file.exists():
            self.print_error(
                f"Requirements file not found: {self.requirements_file}"
            )
            return False

        try:
            self.print_info(
                f"Installing dependencies from {self.requirements_file}..."
            )
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    str(self.requirements_file),
                ],
                check=True,
            )
            self.print_success("Dependencies installed successfully!")
            return True
        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to install dependencies: {e}")
            return False

    def update_env_file(self) -> bool:
        """
        Update the .env file with the private key path.

        Returns:
            True if .env file was updated successfully, False otherwise
        """
        self.print_header("Step 5: Update .env File with Private Key Path")

        # Get the absolute path of the private key
        default_key_path = str(self.private_key_path.resolve())

        self.print_info(f"Default private key location: {default_key_path}")

        if not self.private_key_path.exists():
            self.print_warning(
                "Private key file not found at default location!"
            )
            self.print_info(
                "Please ensure the key file exists before continuing."
            )

        print(
            f"\n{Colors.BOLD}Enter the absolute path to your private key:{Colors.ENDC}"
        )
        print(
            f"{Colors.OKCYAN}(Press Enter to use default: {default_key_path}){Colors.ENDC}"
        )

        user_input = input(
            f"{Colors.BOLD}Private key path: {Colors.ENDC}"
        ).strip()

        if user_input:
            key_path = Path(user_input)
            if not key_path.is_absolute():
                self.print_warning(
                    "Path is not absolute. Converting to absolute path..."
                )
                key_path = key_path.resolve()
        else:
            key_path = self.private_key_path.resolve()

        # Verify the key file exists
        if not key_path.exists():
            self.print_error(f"Private key file not found at: {key_path}")
            if not self.confirm_action("Continue anyway and add path to .env?"):
                return False
        else:
            self.print_success(f"Private key file verified: {key_path}")

        # Read existing .env file if it exists
        env_lines = []
        key_path_found = False

        if self.env_file.exists():
            with open(self.env_file, "r") as f:
                env_lines = f.readlines()

            # Update existing SNOWFLAKE_PRIVATE_KEY_PATH if present
            for i, line in enumerate(env_lines):
                if line.startswith("SNOWFLAKE_PRIVATE_KEY_PATH="):
                    env_lines[i] = f"SNOWFLAKE_PRIVATE_KEY_PATH={key_path}\n"
                    key_path_found = True
                    break

        # If not found, add it
        if not key_path_found:
            # If file doesn't exist, copy from .env.example
            if not self.env_file.exists():
                env_example = self.project_root / ".env.example"
                if env_example.exists():
                    self.print_info("Creating .env file from .env.example...")
                    with open(env_example, "r") as f:
                        env_lines = f.readlines()

                    # Update the SNOWFLAKE_PRIVATE_KEY_PATH line
                    for i, line in enumerate(env_lines):
                        if line.startswith("SNOWFLAKE_PRIVATE_KEY_PATH="):
                            env_lines[i] = (
                                f"SNOWFLAKE_PRIVATE_KEY_PATH={key_path}\n"
                            )
                            key_path_found = True
                            break

            # If still not found, append it
            if not key_path_found:
                if env_lines and not env_lines[-1].endswith("\n"):
                    env_lines.append("\n")
                env_lines.append(f"SNOWFLAKE_PRIVATE_KEY_PATH={key_path}\n")

        # Write back to .env file
        try:
            with open(self.env_file, "w") as f:
                f.writelines(env_lines)

            self.print_success(f"Updated .env file: {self.env_file}")
            self.print_success(f"SNOWFLAKE_PRIVATE_KEY_PATH={key_path}")

            print(f"\n{Colors.BOLD}Important:{Colors.ENDC}")
            print(
                "  * Make sure to fill in other Snowflake credentials in .env"
            )
            print("  * Required: SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER")
            print(f"  * Edit the file: {self.env_file}\n")

            return True

        except Exception as e:
            self.print_error(f"Failed to update .env file: {e}")
            return False

    def test_connection(self, detailed: bool = False) -> bool:
        """
        Test the Snowflake connection with the new key pair authentication.

        Args:
            detailed: If True, run a full test. If False, just a quick connection check.

        Returns:
            True if connection test succeeds, False otherwise
        """
        self.print_header("Test Snowflake Connection")

        # Check if dependencies are installed
        try:
            import importlib.util

            if importlib.util.find_spec("snowflake.connector") is None:
                raise ImportError("snowflake-connector-python not found")
        except ImportError:
            self.print_error("snowflake-connector-python is not installed!")
            self.print_info("Install it using: pip install -r requirements.txt")
            return False

        # Load environment variables
        try:
            from dotenv import load_dotenv

            load_dotenv(self.env_file)
        except ImportError:
            self.print_warning(
                "python-dotenv not installed. Make sure env vars are set manually."
            )

        # Get Snowflake credentials
        account = os.getenv("SNOWFLAKE_ACCOUNT")
        user = os.getenv("SNOWFLAKE_USER")
        warehouse = os.getenv("SNOWFLAKE_WAREHOUSE")
        database = os.getenv("SNOWFLAKE_DATABASE")
        schema = os.getenv("SNOWFLAKE_SCHEMA")
        private_key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")

        # Check required variables
        missing_vars = []
        for var_name, var_value in [
            ("SNOWFLAKE_ACCOUNT", account),
            ("SNOWFLAKE_USER", user),
            ("SNOWFLAKE_PRIVATE_KEY_PATH", private_key_path),
        ]:
            if not var_value:
                missing_vars.append(var_name)

        if missing_vars:
            self.print_error(
                f"Missing environment variables: {', '.join(missing_vars)}"
            )
            self.print_info(f"Please configure these in {self.env_file}")
            return False

        # Check if private key file exists
        key_file = Path(private_key_path)
        if not key_file.is_absolute():
            key_file = self.project_root / private_key_path

        if not key_file.exists():
            self.print_error(f"Private key file not found: {key_file}")
            return False

        self.print_info("Testing Snowflake connection...")
        print(f"\n{Colors.BOLD}Connection Details:{Colors.ENDC}")
        print(f"  Account:   {account}")
        print(f"  User:      {user}")
        print(f"  Warehouse: {warehouse or '(not set)'}")
        print(f"  Database:  {database or '(not set)'}")
        print(f"  Schema:    {schema or '(not set)'}")
        print(f"  Auth:      Key Pair ({key_file})\n")

        try:
            # Use the SnowflakeClient class
            from shared.snowflake.client import SnowflakeClient

            self.print_info("Connecting to Snowflake...")
            with SnowflakeClient() as client:
                self.print_success(
                    "Connection successful! No MFA prompt required!"
                )

                # Run a test query
                if detailed:
                    self.print_info("Running test query...")
                    result = client.execute(
                        "SELECT CURRENT_VERSION(), CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE()",
                        fetch="one",
                    )

                    print(f"\n{Colors.BOLD}Connection Info:{Colors.ENDC}")
                    print(f"  Version:   {result[0]}")
                    print(f"  User:      {result[1]}")
                    print(f"  Role:      {result[2]}")
                    print(f"  Warehouse: {result[3]}")

            self.print_success("Connection test completed successfully!")
            return True

        except Exception as e:
            self.print_error(f"Connection test failed: {e}")
            print(f"\n{Colors.FAIL}Error details:{Colors.ENDC}")
            print(f"  {str(e)}\n")

            print(f"{Colors.BOLD}Troubleshooting tips:{Colors.ENDC}")
            print(
                "  1. Verify the public key was added to Snowflake user account"
            )
            print(
                "  2. Check that SNOWFLAKE_USER matches the user with the public key"
            )
            print("  3. Ensure private key file has correct permissions (600)")
            return False

    def show_current_config(self) -> None:
        """Display current configuration status."""
        self.print_header("Current Configuration")

        # Check keys
        print(f"{Colors.BOLD}RSA Keys:{Colors.ENDC}")
        if self.private_key_path.exists():
            self.print_success(f"Private key exists: {self.private_key_path}")
            # Check permissions on Unix
            if os.name != "nt":
                perms = oct(os.stat(self.private_key_path).st_mode)[-3:]
                if perms == "600":
                    self.print_success(f"Permissions are correct: {perms}")
                else:
                    self.print_warning(
                        f"Permissions are {perms}, should be 600"
                    )
        else:
            self.print_error(f"Private key not found: {self.private_key_path}")

        if self.public_key_path.exists():
            self.print_success(f"Public key exists: {self.public_key_path}")
        else:
            self.print_error(f"Public key not found: {self.public_key_path}")

        # Check .env file
        print(f"\n{Colors.BOLD}Environment Configuration:{Colors.ENDC}")
        if self.env_file.exists():
            self.print_success(f".env file exists: {self.env_file}")

            with open(self.env_file, "r") as f:
                env_content = f.read()

            required_vars = [
                "SNOWFLAKE_ACCOUNT",
                "SNOWFLAKE_USER",
                "SNOWFLAKE_PRIVATE_KEY_PATH",
            ]

            for var in required_vars:
                if var in env_content:
                    # Get the value
                    for line in env_content.split("\n"):
                        if line.startswith(f"{var}="):
                            value = line.split("=", 1)[1].strip()
                            self.print_success(f"{var}={value}")
                            break
                else:
                    self.print_warning(f"{var} not set")
        else:
            self.print_error(f".env file not found: {self.env_file}")

        # Check dependencies
        print(f"\n{Colors.BOLD}Dependencies:{Colors.ENDC}")
        # Mapping of pip package names to Python import names
        required_packages = {
            "snowflake-connector-python": "snowflake.connector",
            "cryptography": "cryptography",
            "python-dotenv": "dotenv",
            "pyperclip": "pyperclip",
        }
        for package_name, import_name in required_packages.items():
            try:
                __import__(import_name)
                self.print_success(f"{package_name} is installed")
            except ImportError:
                self.print_warning(f"{package_name} is NOT installed")

    def run_full_setup(self) -> bool:
        """
        Run the complete setup process.

        Returns:
            True if setup completes successfully, False otherwise
        """
        print(f"\n{Colors.BOLD}{Colors.HEADER}")
        print("=" * 70)
        print("  Snowflake Key Pair Authentication - Full Setup")
        print("=" * 70)
        print(f"{Colors.ENDC}\n")

        print(f"{Colors.WARNING}SECURITY REMINDER:{Colors.ENDC}")
        print(
            "  * Your private key (rsa_key.p8) will NEVER be committed to git"
        )
        print("  * Keep your private key secure and never share it")
        print("  * Only the public key should be shared with Snowflake\n")

        if not self.confirm_action("Ready to start the setup?", default=True):
            print("Setup cancelled by user.")
            return False

        # Step 1: Generate keys
        if not self.setup_keys():
            self.print_error("Setup failed at key generation step")
            return False

        # Step 2: Extract public key
        public_key_content = self.extract_public_key()
        if not public_key_content:
            self.print_error("Setup failed at public key extraction step")
            return False

        # Step 3: Configure Snowflake
        if not self.configure_snowflake(public_key_content):
            self.print_error("Setup incomplete: Snowflake not configured")
            return False

        # Step 4: Check dependencies
        if not self.check_dependencies():
            self.print_error("Setup incomplete: Dependencies not satisfied")
            return False

        # Step 5: Update .env file with private key path
        if not self.update_env_file():
            self.print_error("Setup incomplete: .env file not configured")
            return False

        # Step 6: Test connection
        self.print_info("\nNow let's test the connection...")
        self.test_connection(detailed=True)

        # Final summary
        self.print_header("Setup Complete!")
        print(f"{Colors.OKGREEN}✓ RSA key pair generated{Colors.ENDC}")
        print(f"{Colors.OKGREEN}✓ Public key added to Snowflake{Colors.ENDC}")
        print(f"{Colors.OKGREEN}✓ Dependencies checked{Colors.ENDC}")
        print(
            f"{Colors.OKGREEN}✓ .env file updated with private key path{Colors.ENDC}\n"
        )

        print(f"{Colors.BOLD}Next steps:{Colors.ENDC}")
        print("  * Test your connection using option 2 from the menu")
        print("  * You should no longer see MFA prompts\n")

        return True

    def show_menu(self) -> None:
        """Display the main menu."""
        print(f"\n{Colors.BOLD}{Colors.HEADER}")
        print("=" * 70)
        print("  Snowflake Key Pair Authentication Setup")
        print("=" * 70)
        print(f"{Colors.ENDC}\n")

        print(f"{Colors.BOLD}Main Menu:{Colors.ENDC}\n")
        print(
            f"{Colors.OKCYAN}1.{Colors.ENDC} Run full setup (generate keys, configure Snowflake, etc.)"
        )
        print(
            f"{Colors.OKCYAN}2.{Colors.ENDC} Test Snowflake connection (quick check)"
        )
        print(
            f"{Colors.OKCYAN}3.{Colors.ENDC} Test Snowflake connection (detailed)"
        )
        print(f"{Colors.OKCYAN}4.{Colors.ENDC} Show current configuration")
        print(f"{Colors.OKCYAN}5.{Colors.ENDC} Regenerate RSA keys only")
        print(f"{Colors.OKCYAN}6.{Colors.ENDC} Show public key for Snowflake")
        print(f"{Colors.OKCYAN}7.{Colors.ENDC} Install dependencies")
        print(
            f"{Colors.OKCYAN}8.{Colors.ENDC} Update .env file with private key path"
        )
        print(f"{Colors.OKCYAN}0.{Colors.ENDC} Exit\n")

    def run_interactive(self) -> None:
        """Run the interactive menu."""
        while True:
            self.show_menu()
            choice = input(
                f"{Colors.BOLD}Enter your choice [0-8]: {Colors.ENDC}"
            ).strip()

            if choice == "1":
                self.run_full_setup()
                input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")

            elif choice == "2":
                self.test_connection(detailed=False)
                input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")

            elif choice == "3":
                self.test_connection(detailed=True)
                input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")

            elif choice == "4":
                self.show_current_config()
                input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")

            elif choice == "5":
                self.setup_keys()
                input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")

            elif choice == "6":
                public_key_content = self.extract_public_key()
                if public_key_content:
                    print(f"\n{Colors.BOLD}Full Public Key:{Colors.ENDC}")
                    print(f"{Colors.OKCYAN}{public_key_content}{Colors.ENDC}\n")
                    print(f"{Colors.BOLD}Use this in Snowflake:{Colors.ENDC}")
                    username = input(
                        f"{Colors.BOLD}Enter your Snowflake username (or press Enter to skip): {Colors.ENDC}"
                    ).strip()
                    if username:
                        sql = f"ALTER USER {username} SET RSA_PUBLIC_KEY='{public_key_content}';"
                        print(f"\n{Colors.OKBLUE}{sql}{Colors.ENDC}\n")
                input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")

            elif choice == "7":
                self.install_dependencies()
                input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")

            elif choice == "8":
                self.update_env_file()
                input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")

            elif choice == "0":
                print(
                    f"\n{Colors.OKGREEN}Thank you for using Snowflake Setup!{Colors.ENDC}\n"
                )
                break

            else:
                self.print_error(
                    "Invalid choice. Please enter a number between 0 and 8."
                )
                input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")


def main():
    """Main entry point for the setup script."""
    try:
        setup = SnowflakeSetup()

        # Check if running in virtual environment
        in_venv = hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        )

        if not in_venv:
            print(
                f"{Colors.WARNING}⚠ Warning: Not running in a virtual environment!{Colors.ENDC}"
            )
            print(
                f"{Colors.WARNING}Some dependencies may not be available.{Colors.ENDC}\n"
            )
            print(f"{Colors.BOLD}To activate the venv:{Colors.ENDC}")
            print(f"  cd {setup.project_root}")
            print("  source venv/bin/activate")
            print("  cd backend")
            print("  python setup_snowflake.py\n")

            response = (
                input(f"{Colors.BOLD}Continue anyway? [y/N]: {Colors.ENDC}")
                .strip()
                .lower()
            )
            if response not in ["y", "yes"]:
                print("Exiting. Please activate venv and try again.")
                sys.exit(0)
            print()  # Extra line for spacing

        # Check for command line arguments
        if len(sys.argv) > 1:
            command = sys.argv[1].lower()

            if command == "test":
                # Quick test mode
                detailed = "--detailed" in sys.argv
                success = setup.test_connection(detailed=detailed)
                sys.exit(0 if success else 1)

            elif command == "config":
                # Show configuration
                setup.show_current_config()
                sys.exit(0)

            elif command == "setup":
                # Run full setup
                success = setup.run_full_setup()
                sys.exit(0 if success else 1)

            elif command == "help":
                # Show help
                print("Snowflake Key Pair Authentication Setup\n")
                print("Usage:")
                print(
                    "  python setup_snowflake.py              Interactive menu (default)"
                )
                print("  python setup_snowflake.py setup        Run full setup")
                print(
                    "  python setup_snowflake.py test         Test connection (quick)"
                )
                print(
                    "  python setup_snowflake.py test --detailed   Test connection (detailed)"
                )
                print(
                    "  python setup_snowflake.py config       Show current configuration"
                )
                print(
                    "  python setup_snowflake.py help         Show this help message"
                )
                sys.exit(0)

            else:
                print(f"Unknown command: {command}")
                print(
                    "Run 'python setup_snowflake.py help' for usage information"
                )
                sys.exit(1)

        # No arguments - run interactive menu
        setup.run_interactive()

    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Setup interrupted by user.{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.FAIL}Unexpected error: {e}{Colors.ENDC}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
