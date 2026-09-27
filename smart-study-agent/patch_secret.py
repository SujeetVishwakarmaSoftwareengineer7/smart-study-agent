"""Patch .env with a generated FLASK_SECRET_KEY if it is still placeholder."""
import secrets, re

with open('.env', 'r') as f:
    content = f.read()

if 'change-this-to-a-random-secret-key' in content:
    new_key = secrets.token_hex(32)
    content = content.replace('change-this-to-a-random-secret-key', new_key)
    with open('.env', 'w') as f:
        f.write(content)
    print('Flask secret key generated and saved.')
else:
    print('Flask secret key already set.')
