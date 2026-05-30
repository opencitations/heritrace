# SPDX-FileCopyrightText: 2024-2025 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import datetime
import ipaddress
import os
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from config import Config
from heritrace import create_app


def get_ssl_context() -> tuple[str, str]:
    cert_dir = Path(__file__).parent / "ssl"
    cert_file = cert_dir / "cert.pem"
    key_file = cert_dir / "key.pem"

    cert_dir.mkdir(parents=True, exist_ok=True)

    if not (cert_file.exists() and key_file.exists()):
        key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )

        with key_file.open("wb") as f:
            f.write(
                key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "IT"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Bologna"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "Bologna"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "OpenCitations"),
                x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
            ]
        )

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
            .not_valid_after(
                datetime.datetime.now(datetime.timezone.utc)
                + datetime.timedelta(days=365)
            )
            .add_extension(
                x509.SubjectAlternativeName(
                    [
                        x509.DNSName("localhost"),
                        x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                    ]
                ),
                critical=False,
            )
            .sign(key, hashes.SHA256(), default_backend())
        )

        with cert_file.open("wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        key_file.chmod(0o600)

    return (str(cert_file), str(key_file))


app = create_app(Config)

if __name__ == "__main__":
    env = os.getenv("FLASK_ENV", "development")

    run_args = {"host": "0.0.0.0", "port": 5000}

    if env == "development":
        run_args.update({"debug": True, "ssl_context": get_ssl_context()})
    elif env == "demo":
        run_args.update({"debug": True})

    extra_files = []
    if app.config.get("SHACL_PATH") and app.config["SHACL_PATH"].exists():
        extra_files.append(str(app.config["SHACL_PATH"]))
    if (
        app.config.get("DISPLAY_RULES_PATH")
        and app.config["DISPLAY_RULES_PATH"].exists()
    ):
        extra_files.append(str(app.config["DISPLAY_RULES_PATH"]))

    if extra_files:
        run_args["extra_files"] = extra_files

    app.run(**run_args)
