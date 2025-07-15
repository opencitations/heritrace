import datetime
import ipaddress
import os

from config import Config
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from heritrace import create_app


def get_ssl_context():
    """Get SSL context if certificates exist, or create them if they don't."""
    cert_dir = os.path.join(os.path.dirname(__file__), 'ssl')
    cert_file = os.path.join(cert_dir, 'cert.pem')
    key_file = os.path.join(cert_dir, 'key.pem')

    if not os.path.exists(cert_dir):
        os.makedirs(cert_dir)

    if not (os.path.exists(cert_file) and os.path.exists(key_file)):
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        with open(key_file, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"IT"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Bologna"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, u"Bologna"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"OpenCitations"),
            x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
        ])

        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.now(datetime.timezone.utc)
        ).not_valid_after(
            # Our certificate will be valid for 1 year
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([x509.DNSName(u"localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
            critical=False
        # Sign our certificate with our private key
        ).sign(key, hashes.SHA256(), default_backend())

        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

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