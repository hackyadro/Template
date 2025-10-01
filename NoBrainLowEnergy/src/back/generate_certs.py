#!/usr/bin/env python3
"""
Script to generate TLS certificates for MQTT broker and client
Run this script to create self-signed certificates for testing
"""

import os
import subprocess
import sys
from pathlib import Path

def create_certs_directory():
    """Create certificates directory if it doesn't exist"""
    certs_dir = Path("certs")
    certs_dir.mkdir(exist_ok=True)
    return certs_dir

def generate_ca_cert(certs_dir: Path):
    """Generate Certificate Authority certificate"""
    print("Generating CA certificate...")
    
    # Generate CA private key
    subprocess.run([
        "openssl", "genrsa", "-out", str(certs_dir / "ca.key"), "2048"
    ], check=True)
    
    # Generate CA certificate
    subprocess.run([
        "openssl", "req", "-new", "-x509", "-days", "365",
        "-key", str(certs_dir / "ca.key"),
        "-out", str(certs_dir / "ca.crt"),
        "-subj", "/C=US/ST=State/L=City/O=Organization/CN=NoBrainLowEnergy-CA"
    ], check=True)
    
    print(f"CA certificate generated: {certs_dir / 'ca.crt'}")

def generate_server_cert(certs_dir: Path):
    """Generate server certificate for MQTT broker"""
    print("Generating server certificate...")
    
    # Generate server private key
    subprocess.run([
        "openssl", "genrsa", "-out", str(certs_dir / "server.key"), "2048"
    ], check=True)
    
    # Generate server certificate signing request
    subprocess.run([
        "openssl", "req", "-new",
        "-key", str(certs_dir / "server.key"),
        "-out", str(certs_dir / "server.csr"),
        "-subj", "/C=US/ST=State/L=City/O=Organization/CN=localhost"
    ], check=True)
    
    # Generate server certificate signed by CA
    subprocess.run([
        "openssl", "x509", "-req", "-days", "365",
        "-in", str(certs_dir / "server.csr"),
        "-CA", str(certs_dir / "ca.crt"),
        "-CAkey", str(certs_dir / "ca.key"),
        "-CAcreateserial",
        "-out", str(certs_dir / "server.crt"),
        "-extensions", "v3_req"
    ], check=True)
    
    # Clean up CSR file
    (certs_dir / "server.csr").unlink()
    
    print(f"Server certificate generated: {certs_dir / 'server.crt'}")

def generate_client_cert(certs_dir: Path):
    """Generate client certificate for MQTT client"""
    print("Generating client certificate...")
    
    # Generate client private key
    subprocess.run([
        "openssl", "genrsa", "-out", str(certs_dir / "client.key"), "2048"
    ], check=True)
    
    # Generate client certificate signing request
    subprocess.run([
        "openssl", "req", "-new",
        "-key", str(certs_dir / "client.key"),
        "-out", str(certs_dir / "client.csr"),
        "-subj", "/C=US/ST=State/L=City/O=Organization/CN=client"
    ], check=True)
    
    # Generate client certificate signed by CA
    subprocess.run([
        "openssl", "x509", "-req", "-days", "365",
        "-in", str(certs_dir / "client.csr"),
        "-CA", str(certs_dir / "ca.crt"),
        "-CAkey", str(certs_dir / "ca.key"),
        "-CAcreateserial",
        "-out", str(certs_dir / "client.crt")
    ], check=True)
    
    # Clean up CSR file
    (certs_dir / "client.csr").unlink()
    
    print(f"Client certificate generated: {certs_dir / 'client.crt'}")

def set_permissions(certs_dir: Path):
    """Set appropriate permissions for certificate files"""
    print("Setting certificate permissions...")
    
    # Set permissions for private keys (readable only by owner)
    for key_file in certs_dir.glob("*.key"):
        key_file.chmod(0o600)
    
    # Set permissions for certificates (readable by owner and group)
    for cert_file in certs_dir.glob("*.crt"):
        cert_file.chmod(0o644)

def create_mosquitto_config(certs_dir: Path):
    """Create a sample Mosquitto configuration with TLS"""
    config_content = f"""# Mosquitto Configuration for NoBrainLowEnergy
# Save this as mosquitto.conf

# General settings
listener 1883 localhost
protocol mqtt

# TLS listener
listener 8883
protocol mqtt
cafile {certs_dir.absolute()}/ca.crt
certfile {certs_dir.absolute()}/server.crt
keyfile {certs_dir.absolute()}/server.key
require_certificate true
use_identity_as_username true

# Logging
log_type error
log_type warning  
log_type notice
log_type information
log_type debug

# Persistence
persistence true
persistence_location /tmp/mosquitto/

# Security
allow_anonymous false

# Password file (create with mosquitto_passwd)
# password_file /path/to/passwd

# ACL file (optional)
# acl_file /path/to/acl
"""
    
    config_file = certs_dir.parent / "mosquitto.conf"
    with open(config_file, "w") as f:
        f.write(config_content)
    
    print(f"Mosquitto configuration created: {config_file}")
    print("To use this configuration:")
    print(f"  mosquitto -c {config_file}")

def main():
    """Main function to generate all certificates"""
    print("NoBrainLowEnergy TLS Certificate Generator")
    print("=" * 50)
    
    # Check if OpenSSL is available
    try:
        subprocess.run(["openssl", "version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: OpenSSL is not installed or not in PATH")
        print("Please install OpenSSL to generate certificates")
        sys.exit(1)
    
    try:
        # Create certificates directory
        certs_dir = create_certs_directory()
        
        # Generate certificates
        generate_ca_cert(certs_dir)
        generate_server_cert(certs_dir)
        generate_client_cert(certs_dir)
        
        # Set permissions
        set_permissions(certs_dir)
        
        # Create Mosquitto config
        create_mosquitto_config(certs_dir)
        
        print("\n" + "=" * 50)
        print("Certificate generation completed successfully!")
        print(f"Certificates are stored in: {certs_dir.absolute()}")
        print("\nGenerated files:")
        print("  - ca.crt: Certificate Authority certificate")
        print("  - ca.key: Certificate Authority private key")
        print("  - server.crt: MQTT broker certificate")
        print("  - server.key: MQTT broker private key")
        print("  - client.crt: MQTT client certificate")
        print("  - client.key: MQTT client private key")
        print("  - mosquitto.conf: Sample Mosquitto configuration")
        print("\nIMPORTANT: These are self-signed certificates for testing only!")
        print("For production, use certificates from a trusted CA.")
        
    except subprocess.CalledProcessError as e:
        print(f"Error generating certificates: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()