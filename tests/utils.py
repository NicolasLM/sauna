import tempfile
import os.path as path

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


# https://gist.github.com/bloodearnest/9017111a313777b9cce5
def generate_selfsigned_cert(hostname, from_date, to_date):
    # Generate our key
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=1024,
        backend=default_backend()
    )

    name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, hostname)
    ])
    alt_names = x509.SubjectAlternativeName([
        # best practice seem to be to include the hostname in the SAN, which
        # *SHOULD* mean COMMON_NAME is ignored.
        x509.DNSName(hostname)
    ])
    # path_len=0 means this cert can only sign itself, not other certs.
    basic_contraints = x509.BasicConstraints(ca=True, path_length=0)
    cert = (
        x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(1000)
            .not_valid_before(from_date)
            .not_valid_after(to_date)
            .add_extension(basic_contraints, False)
            .add_extension(alt_names, False)
            .sign(key, hashes.SHA256(), default_backend())
    )
    cert_pem = cert.public_bytes(encoding=serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    return cert_pem, key_pem


def generate_selfsigned_cert_files(hostname, from_date, to_date):
    cert, key = generate_selfsigned_cert(hostname, from_date, to_date)

    temp_dir = tempfile.TemporaryDirectory(prefix='sauna-test-')
    cert_file = path.join(temp_dir.name, 'ssl-cert.crt')
    key_file = path.join(temp_dir.name, 'ssl-cert.pem')

    try:
        with open(cert_file, 'wb') as f:
            f.write(cert)
        with open(key_file, 'wb') as f:
            f.write(key)
    except Exception:
        temp_dir.cleanup()
        raise

    return cert_file, key_file, temp_dir
