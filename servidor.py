"""SESI Conecta — servidor local. Python 3.10+, sem dependências externas."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlsplit
import argparse
import json
import os
import secrets
import sqlite3
import socket
import time
import uuid

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / 'public'
DATA_DIR = Path(os.environ.get('DATA_DIR', str(ROOT)))
DB_PATH = DATA_DIR / 'chat.sqlite3'
HOSTED = os.environ.get('HOSTED', '0') == '1'
AVATARS = ['🚀', '⚡', '🎮', '🧠', '🤖', '🎨', '🌻', '🐱']
EMOJIS = ['👍', '❤️', '😂', '🎉', '🔥', '👀']
COLORS = ['#7864e8', '#d16b38', '#268c78', '#467bc4', '#ba5792']
ROOMS = ['geral', 'projetos', 'ajuda']

class ChatError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status

def valid(value, maximum, label):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise ChatError(f'{label} inválido.')
    return value.strip()

def database():
    db = sqlite3.connect(DB_PATH, timeout=20)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db

def initialize():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with database() as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript((ROOT / 'schema.sql').read_text(encoding='utf-8'))

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

    def log_message(self, *_):
        pass

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        super().end_headers()

    def response(self, body, status=200, cookie=None):
        data = json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if urlsplit(self.path).path == '/health':
            try:
                with database() as db:
                    db.execute('SELECT 1 FROM groups LIMIT 1').fetchone()
                return self.response({'ok': True})
            except Exception:
                return self.response({'ok': False}, 503)
        if urlsplit(self.path).path == '/api/chat':
            return self.chat({})
        if urlsplit(self.path).path == '/':
            query = urlsplit(self.path).query
            self.path = '/index.html' + ('?' + query if query else '')
        # Apenas arquivos da interface podem ser servidos; nunca o banco de dados.
        if urlsplit(self.path).path not in ['/index.html', '/chat.js', '/chat.css', '/favicon.svg']:
            self.send_error(404)
            return
        super().do_GET()

    def do_POST(self):
        if urlsplit(self.path).path != '/api/chat':
            self.send_error(404)
            return
        origin = self.headers.get('Origin')
        host = self.headers.get('Host', '')
        expected_origin = ('https://' if HOSTED else 'http://') + host
        if origin and origin != expected_origin:
            return self.response({'error': 'Origem não permitida.'}, 403)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 16000:
                raise ChatError('Dados muito grandes ou inválidos.', 413)
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ChatError('Dados inválidos.')
            self.chat(payload)
        except (ValueError, json.JSONDecodeError):
            self.response({'error': 'Dados inválidos.'}, 400)
        except ChatError as error:
            self.response({'error': str(error)}, error.status)

    def chat(self, p):
        db = database()
        try:
            result, cookie = self.operate(db, p)
            db.commit()
            self.response(result, cookie=cookie)
        except ChatError as error:
            db.rollback()
            self.response({'error': str(error)}, error.status)
        except Exception as error:
            db.rollback()
            print('Falha no servidor:', type(error).__name__)
            self.response({'error': 'O servidor está indisponível. Tente novamente.'}, 503)
        finally:
            db.close()

    def operate(self, db, p):
        now = int(time.time() * 1000)
        action = p.get('action')
        one = lambda sql, *a: db.execute(sql, a).fetchone()
        run = lambda sql, *a: db.execute(sql, a)
        if action in ['create', 'join']:
            name = valid(p.get('name'), 24, 'Nome')
            avatar = p.get('avatar') if p.get('avatar') in AVATARS else '🚀'
            if action == 'create':
                group = {'id': str(uuid.uuid4()), 'code': ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(8)), 'name': valid(p.get('groupName'), 40, 'Nome do grupo')}
                run('INSERT INTO groups (id,code,name,created) VALUES (?,?,?,?)', group['id'], group['code'], group['name'], now)
            else:
                group = one('SELECT * FROM groups WHERE code=?', valid(p.get('code'), 8, 'Código').upper())
                if group is None:
                    raise ChatError('Grupo não encontrado. Confira o código.', 404)
            if one('SELECT count(*) AS n FROM sessions WHERE gid=? AND seen>?', group['id'], now-20000)['n'] >= 100:
                raise ChatError('Este grupo está cheio. Tente novamente mais tarde.', 409)
            sid, token = str(uuid.uuid4()), str(uuid.uuid4()) + str(uuid.uuid4())
            run('INSERT INTO sessions (id,token,gid,name,avatar,color,seen,expires) VALUES (?,?,?,?,?,?,?,?)', sid, token, group['id'], name, avatar, secrets.choice(COLORS), now, now+7*86400000)
            return {'ok': True}, f'sesi_session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=604800' + ('; Secure' if HOSTED else '')
        cookies = SimpleCookie()
        cookies.load(self.headers.get('Cookie', ''))
        token = cookies['sesi_session'].value if 'sesi_session' in cookies else ''
        s = one('SELECT * FROM sessions WHERE token=? AND expires>?', token, now)
        if s is None:
            raise ChatError('Entre no grupo para conversar.', 401)
        visible = 'm.gid=? AND (m.target IS NULL OR m.sender=? OR m.target=?)'
        access = (s['gid'], s['id'], s['id'])
        if self.command == 'GET':
            run('UPDATE sessions SET seen=? WHERE id=?', now, s['id'])
            group = dict(one('SELECT name,code FROM groups WHERE id=?', s['gid']))
            users = [dict(r) for r in run('SELECT id,name,avatar,color,seen,typing,channel FROM sessions WHERE gid=? AND expires>? ORDER BY name', s['gid'], now)]
            for user in users:
                if isinstance(user['channel'], str) and user['channel'].startswith('dm:') and user['id'] != s['id'] and user['channel'] != 'dm:' + s['id']:
                    user['typing'] = 0
                    user['channel'] = None
            messages = [dict(r) for r in run(f'SELECT m.*,s.name,s.avatar,s.color FROM messages m JOIN sessions s ON m.sender=s.id WHERE {visible} ORDER BY m.created DESC,m.id DESC LIMIT 200', *access)][::-1]
            reactions = [dict(r) for r in run(f'SELECT r.mid,r.uid,r.emoji FROM reactions r JOIN messages m ON r.mid=m.id WHERE {visible} AND m.deleted=0', *access)]
            return {'me': {k: s[k] for k in ['id', 'name', 'avatar', 'color']}, 'group': group, 'users': users, 'messages': messages, 'reactions': reactions, 'now': now}, None
        if action == 'leave':
            run('UPDATE sessions SET expires=0,seen=0,typing=0 WHERE id=?', s['id'])
            return {'ok': True}, 'sesi_session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0' + ('; Secure' if HOSTED else '')
        if action == 'typing':
            channel = valid(p.get('channel'), 80, 'Conversa')
            if channel not in ROOMS and not channel.startswith('dm:'):
                raise ChatError('Sala inválida.')
            if channel.startswith('dm:') and (channel[3:] == s['id'] or not one('SELECT id FROM sessions WHERE id=? AND gid=? AND expires>?', channel[3:], s['gid'], now)):
                raise ChatError('Participante indisponível.')
            run('UPDATE sessions SET typing=?,channel=?,seen=? WHERE id=?', now+4000 if p.get('typing') else 0, channel, now, s['id'])
        elif action == 'send':
            body, channel = valid(p.get('body'), 3000, 'Mensagem'), valid(p.get('channel'), 80, 'Conversa')
            target = None
            if channel.startswith('dm:'):
                target = channel[3:]
                if target == s['id'] or not one('SELECT id FROM sessions WHERE id=? AND gid=? AND expires>?', target, s['gid'], now):
                    raise ChatError('Participante indisponível.')
            elif channel not in ROOMS:
                raise ChatError('Sala inválida.')
            reply = p.get('reply') or None
            if reply:
                r = one(f'SELECT m.* FROM messages m WHERE m.id=? AND {visible}', str(reply), *access)
                if not r or r['deleted'] or (target and (not r['target'] or target not in [r['sender'], r['target']])) or (not target and (r['target'] or r['channel'] != channel)):
                    raise ChatError('Resposta inválida.')
            mid = valid(p.get('id'), 40, 'Identificador')
            try:
                uuid.UUID(mid)
            except ValueError:
                raise ChatError('Identificador inválido.')
            old = one('SELECT sender FROM messages WHERE id=?', mid)
            if old:
                if old['sender'] != s['id']:
                    raise ChatError('Identificador em uso.', 409)
                return {'ok': True}, None
            if not run('UPDATE sessions SET last_sent=?,typing=0 WHERE id=? AND last_sent<?', now, s['id'], now-500).rowcount:
                raise ChatError('Aguarde um instante antes de enviar outra mensagem.', 429)
            run('INSERT INTO messages (id,gid,sender,channel,target,body,reply,created) VALUES (?,?,?,?,?,?,?,?)', mid, s['gid'], s['id'], 'privado' if target else channel, target, body, reply, now)
        elif action in ['react', 'delete']:
            m = one(f'SELECT m.id,m.sender,m.deleted FROM messages m WHERE m.id=? AND {visible}', str(p.get('mid')), *access)
            if not m or m['deleted']:
                raise ChatError('Mensagem indisponível.', 404)
            if action == 'delete':
                if m['sender'] != s['id']:
                    raise ChatError('Você só pode apagar suas mensagens.', 403)
                run("UPDATE messages SET deleted=1,body='',reply=NULL WHERE id=?", m['id'])
                run('DELETE FROM reactions WHERE mid=?', m['id'])
            else:
                emoji = p.get('emoji')
                if emoji not in EMOJIS:
                    raise ChatError('Reação inválida.')
                old = one('SELECT mid FROM reactions WHERE mid=? AND uid=? AND emoji=?', m['id'], s['id'], emoji)
                if old:
                    run('DELETE FROM reactions WHERE mid=? AND uid=? AND emoji=?', m['id'], s['id'], emoji)
                else:
                    run('INSERT OR IGNORE INTO reactions (mid,uid,emoji) VALUES (?,?,?)', m['id'], s['id'], emoji)
        else:
            raise ChatError('Ação inválida.')
        return {'ok': True}, None

def main():
    parser = argparse.ArgumentParser(description='Chat local SESI Conecta')
    parser.add_argument('--porta', type=int, default=int(os.environ.get('PORT', '5000')))
    args = parser.parse_args()
    initialize()
    try:
        server = ThreadingHTTPServer(('0.0.0.0', args.porta), Handler)
    except OSError as error:
        print(f'Não foi possível iniciar na porta {args.porta}: {error}')
        print('Se a porta estiver ocupada, use: python servidor.py --porta 5001')
        return
    print(f'\nSESI Conecta iniciado! Neste computador: http://localhost:{args.porta}')
    try:
        ips = sorted(set(socket.gethostbyname_ex(socket.gethostname())[2]))
        for ip in ips:
            if not ip.startswith('127.'):
                print(f'Na rede local, tente: http://{ip}:{args.porta}')
    except OSError:
        pass
    print('No Windows, use ipconfig para conferir o IPv4 da conexão Wi-Fi.')
    print('Todos devem estar na mesma rede. Ctrl+C encerra o servidor.\n')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServidor encerrado.')
    finally:
        server.server_close()

if __name__ == '__main__':
    main()
