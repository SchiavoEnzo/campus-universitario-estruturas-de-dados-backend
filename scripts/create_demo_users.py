"""Create the two requested administrators without overwriting existing accounts.

Run from the backend directory: .venv/bin/python scripts/create_demo_users.py
The initial passwords are written only to the gitignored private credentials file.
"""
import json
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from campus.auth import auth_db, password_hash, now

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
output = Path(__file__).resolve().parents[1] / '.env.demo-users.json'
credentials = json.loads(output.read_text()) if output.exists() else {}
db = auth_db()
for username, name in [('verissimo', 'Veríssimo'), ('enzo', 'Enzo')]:
    existing = db.users.find_one({'username': username})
    if existing:
        print(name + ': conta já existente, preservada.')
        continue
    password = credentials.setdefault(username, {}).setdefault('temporary_password', secrets.token_urlsafe(18))
    credentials[username].update({'name': name, 'username': username, 'role': 'admin'})
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, 'w') as handle:
        json.dump(credentials, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    output.chmod(0o600)
    db.users.insert_one({'username': username, 'name': name, 'role': 'admin',
        'password_hash': password_hash.hash(password), 'must_change_password': True,
        'auth_version': 1, 'created_at': now(), 'disabled': False})
    print(name + ': administrador criado; troca de senha exigida no primeiro acesso.')
print('Senhas temporárias: .env.demo-users.json (privado, ignorado pelo Git).')
