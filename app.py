import os

from config import Config
from heritrace import create_app
from OpenSSL import crypto


def get_ssl_context():
    """Get SSL context if certificates exist, or create them if they don't."""
    # Usa una directory specifica per i certificati
    cert_dir = os.path.join(os.path.dirname(__file__), 'ssl')
    cert_file = os.path.join(cert_dir, 'cert.pem')
    key_file = os.path.join(cert_dir, 'key.pem')
    
    # Crea la directory se non esiste
    if not os.path.exists(cert_dir):
        os.makedirs(cert_dir)
    
    if not (os.path.exists(cert_file) and os.path.exists(key_file)):
        
        # Create a new private key using RSA algorithm
        # RSA is an asymmetric encryption algorithm that uses a pair of keys (public and private)
        # 2048 is the key size in bits - larger numbers mean more security but slower performance
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 2048)
        
        # Create a new self-signed X.509 certificate
        # X.509 is a standard format for public key certificates
        cert = crypto.X509()
        
        # Add all needed hostnames and IPs as Subject Alternative Names
        san_list = [
            b"DNS:localhost",
            b"IP:127.0.0.1"
        ]
        san_extension = crypto.X509Extension(
            b"subjectAltName",
            False,
            b", ".join(san_list)
        )
        cert.add_extensions([san_extension])
        
        cert.get_subject().CN = "localhost"
        
        # Set a unique serial number for the certificate
        # This is required by the X.509 standard
        cert.set_serial_number(1000)
        
        # Set the certificate validity period
        # Start time is now (0 seconds offset)
        cert.gmtime_adj_notBefore(0)
        # End time is one year from now (365 days * 24 hours * 60 minutes * 60 seconds)
        cert.gmtime_adj_notAfter(365*24*60*60)  # Valid for one year
        
        # For a self-signed certificate, the issuer and subject are the same
        cert.set_issuer(cert.get_subject())
        
        # Attach the public key (derived from our private key) to the certificate
        cert.set_pubkey(key)
        
        # Sign the certificate with our private key using SHA256 algorithm
        # This proves that we own the private key
        cert.sign(key, 'sha256')
        
        # Save the certificate and private key to files in PEM format
        # PEM is a base64 encoded format commonly used for certificates
        with open(cert_file, "wb") as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        with open(key_file, "wb") as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
            
        # Aggiungi permessi restrittivi al file della chiave privata
        os.chmod(key_file, 0o600)
    
    return (cert_file, key_file)

app = create_app(Config)

if __name__ == '__main__':
    env = os.getenv('FLASK_ENV', 'development')
    
    run_args = {
        'host': '0.0.0.0',
        'port': 5000
    }
    
    if env == 'development':
        run_args.update({
            'debug': True,
            'ssl_context': get_ssl_context()
        })
    elif env == 'demo':
        run_args.update({
            'debug': True
        })
        
    extra_files = []
    if app.config.get('SHACL_PATH') and os.path.exists(app.config['SHACL_PATH']):
        extra_files.append(app.config['SHACL_PATH'])
    if app.config.get('DISPLAY_RULES_PATH') and os.path.exists(app.config['DISPLAY_RULES_PATH']):
        extra_files.append(app.config['DISPLAY_RULES_PATH'])
    
    if extra_files:
        run_args['extra_files'] = extra_files

    app.run(**run_args)