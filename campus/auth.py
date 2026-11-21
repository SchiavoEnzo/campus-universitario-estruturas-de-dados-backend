"""Password login and revocable, server-side sessions stored in MongoDB."""
import hashlib
import os
import secrets
import unicodedata
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from pwdlib import PasswordHash
from pymongo import ReturnDocument

from .repository import mongo_client

router = APIRouter(prefix="/api/auth", tags=["Autenticação"])
password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash(secrets.token_urlsafe(32))
SESSION_SECONDS = 8 * 60 * 60


def now():
    return datetime.now(timezone.utc)


def normalize_username(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.strip().casefold()) if not unicodedata.combining(c))


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def secure_cookie():
    return bool(os.getenv('VERCEL'))


def cookie_name():
    return '__Host-campus_session' if secure_cookie() else 'campus_session'


@lru_cache(maxsize=1)
def auth_db():
    uri = os.getenv('MONGODB_URI')
    if not uri:
        raise RuntimeError('MONGODB_URI não configurada.')
    db = mongo_client(uri)[os.getenv('MONGODB_DB') or 'campus_viva']
    db.users.create_index('username', unique=True)
    db.auth_sessions.create_index('expires_at', expireAfterSeconds=0)
    db.auth_sessions.create_index('user_id')
    db.auth_attempts.create_index('expires_at', expireAfterSeconds=0)
    return db


def trusted_origin(request):
    allowed = {v.strip().rstrip('/') for v in os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',') if v.strip() and v.strip() != '*'}
    if request.headers.get('origin') not in allowed:
        raise HTTPException(403, 'Origem da solicitação não autorizada.')


def rate_limit(db, key, limit=10):
    stamp = now()
    bucket = int(stamp.timestamp()) // 900
    record = db.auth_attempts.find_one_and_update(
        {'_id': digest(f'{key}:{bucket}')},
        {'$inc': {'count': 1}, '$setOnInsert': {'expires_at': stamp + timedelta(minutes=30)}},
        upsert=True, return_document=ReturnDocument.AFTER,
    )
    if record['count'] > limit:
        raise HTTPException(429, 'Muitas tentativas. Aguarde até 15 minutos e tente novamente.', headers={'Retry-After': '900'})


def public_user(user):
    return {'id': str(user['_id']), 'username': user['username'], 'name': user['name'],
            'role': user['role'], 'must_change_password': user.get('must_change_password', False)}


def create_session(db, user, response):
    token = secrets.token_urlsafe(32)
    session = {'_id': digest(token), 'user_id': user['_id'], 'csrf': secrets.token_urlsafe(32),
               'version': user.get('auth_version', 1), 'expires_at': now() + timedelta(seconds=SESSION_SECONDS)}
    db.auth_sessions.insert_one(session)
    response.set_cookie(cookie_name(), token, max_age=SESSION_SECONDS, path='/',
                        secure=secure_cookie(), httponly=True, samesite='lax')
    return {'user': public_user(user), 'csrf_token': session['csrf']}


def session_user(request: Request, db=Depends(auth_db)):
    token = request.cookies.get(cookie_name(), '')
    if not token or len(token) > 256:
        raise HTTPException(401, 'Entre na sua conta para continuar.')
    session = db.auth_sessions.find_one({'_id': digest(token), 'expires_at': {'$gt': now()}})
    user = db.users.find_one({'_id': session['user_id']}) if session else None
    if not user or user.get('disabled') or user.get('auth_version', 1) != session['version']:
        raise HTTPException(401, 'Sua sessão expirou. Entre novamente.')
    return user, session


def check_csrf(request, session):
    trusted_origin(request)
    if not secrets.compare_digest(request.headers.get('x-csrf-token', ''), session['csrf']):
        raise HTTPException(403, 'Sessão de segurança inválida. Atualize a página.')


def require_session_admin(request: Request, identity=Depends(session_user)):
    user, session = identity
    check_csrf(request, session)
    if user['role'] != 'admin':
        raise HTTPException(403, 'Acesso restrito a administradores.')
    if user.get('must_change_password'):
        raise HTTPException(403, 'Troque sua senha temporária antes de editar.')
    return user


class Login(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=128)


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra='forbid')
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


@router.post('/login')
def login(payload: Login, request: Request, response: Response, db=Depends(auth_db)):
    trusted_origin(request)
    username = normalize_username(payload.username)
    rate_limit(db, 'login:' + username)
    user = db.users.find_one({'username': username})
    valid = password_hash.verify(payload.password, user['password_hash'] if user else DUMMY_HASH)
    if not valid or not user or user.get('disabled'):
        raise HTTPException(401, 'Usuário ou senha inválidos.')
    old_token = request.cookies.get(cookie_name())
    if old_token:
        db.auth_sessions.delete_one({'_id': digest(old_token)})
    return create_session(db, user, response)


@router.get('/me')
def me(identity=Depends(session_user)):
    user, session = identity
    return {'user': public_user(user), 'csrf_token': session['csrf']}


@router.post('/logout', status_code=204)
def logout(request: Request, response: Response, db=Depends(auth_db)):
    trusted_origin(request)
    token = request.cookies.get(cookie_name())
    session = db.auth_sessions.find_one({'_id': digest(token)}) if token else None
    if session:
        check_csrf(request, session)
        db.auth_sessions.delete_one({'_id': session['_id']})
    response.delete_cookie(cookie_name(), path='/', secure=secure_cookie(), httponly=True, samesite='lax')


@router.post('/password')
def change_password(payload: PasswordChange, request: Request, response: Response,
                    identity=Depends(session_user), db=Depends(auth_db)):
    user, session = identity
    check_csrf(request, session)
    rate_limit(db, 'password:' + str(user['_id']))
    if not password_hash.verify(payload.current_password, user['password_hash']):
        raise HTTPException(400, 'Senha atual inválida.')
    if payload.current_password == payload.new_password:
        raise HTTPException(400, 'Escolha uma senha diferente da atual.')
    updated = db.users.find_one_and_update(
        {'_id': user['_id'], 'password_hash': user['password_hash']},
        {'$set': {'password_hash': password_hash.hash(payload.new_password), 'must_change_password': False},
         '$inc': {'auth_version': 1}}, return_document=ReturnDocument.AFTER,
    )
    if not updated:
        raise HTTPException(409, 'A conta mudou. Entre novamente.')
    db.auth_sessions.delete_many({'user_id': user['_id']})
    return create_session(db, updated, response)
