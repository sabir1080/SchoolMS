from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.management.base import BaseCommand

from apps.messaging.push import b64url


class Command(BaseCommand):
    help = "Print a new VAPID key pair for Web Push. Put the private key in the VAPID_PRIVATE_KEY environment variable."

    def handle(self, *args, **options):
        key = ec.generate_private_key(ec.SECP256R1())
        private = b64url(key.private_numbers().private_value.to_bytes(32, "big"))
        public = b64url(key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))
        self.stdout.write(f"VAPID_PRIVATE_KEY={private}\n(public key, sent to browsers automatically: {public})")
