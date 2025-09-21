import os
import re
import sys
import json
import time
from flask import Flask, request, jsonify, render_template, redirect, url_for, Response, stream_with_context
from flask import current_app as app
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import threading
from datetime import datetime,timedelta
import socket
import requests
import traceback
import subprocess
import signal

# Caminho atual do script (server.py)
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))  # Vai até ~/Documents/Face-Scan-Id

# Verifica se o PYTHONPATH já está correto
if project_root not in sys.path:
    # Reexecuta o script com PYTHONPATH ajustado
    print("[INFO] Ajustando PYTHONPATH e reiniciando...")
    os.environ["PYTHONPATH"] = project_root
    subprocess.run(["python3", script_path], env=os.environ)
    sys.exit()

from Site.reconhecimento import iniciar_reconhecimento
import Site.config.config_camera as config_camera


app = Flask(__name__)
executor = ThreadPoolExecutor(max_workers=1)
gerarstream = True

users_lock = Lock()
config_lock = Lock()
last_uid  = None
last_user = None
last_time = None
last_uid_time = None

# Lista de todos os usuários
USERS_PATH = os.path.join(os.path.dirname(__file__), 'data', 'users.json')

# Utilitários
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config', 'config.json')

# Histórico de todas as tentativas de acesso
HISTORICO_PATH = os.path.join(os.path.dirname(__file__), 'data', 'historico.jsonl')

#Histórico de todas a mudanças no sistema
LOG_PATH = os.path.join(os.path.dirname(__file__), 'logs','system_log.log')

# 1) Defina aqui as credenciais desejadas
AUTH_USERNAME = "admin"
AUTH_PASSWORD = "3397"

# 2) Funções de suporte ao Basic Auth
def authenticate():
    """Retorna 401 pra forçar o browser a pedir usuário/senha."""
    return Response(
        """
        <html>
        <head>
            <style>
                body {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    background-color: #f8d7da;
                    font-family: Arial, sans-serif;
                }
                .mensagem {
                    color: #721c24;
                    background-color: #f5c6cb;
                    padding: 40px;
                    border: 2px solid #f5c6cb;
                    font-size: 32px;
                    font-weight: bold;
                    text-align: center;
                    border-radius: 10px;
                }
            </style>
        </head>
        <body>
            <div class="mensagem">
                VOCÊ NÃO TEM AUTORIZAÇÃO DE ACESSAR ESSE SITE,<br>
                ENTRE EM CONTATO COM O ADMINISTRADOR DA PÁGINA.
            </div>
        </body>
        </html>
        """,
        401,
        {"WWW-Authenticate": 'Basic realm="Acesso Restrito"'}
    )

def check_auth(username: str, password: str) -> bool:
    """Verifica se a combinação está correta."""
    return username == AUTH_USERNAME and password == AUTH_PASSWORD
  
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        auth = request.authorization
        if request.endpoint not in ('exibir_logs', 'get_logs'):
            printLOG(f"Tentativa de acesso. IP: {ip} | ROTA: {request.endpoint}", nivel="INFO")

        if not auth:
            if request.path == "/":
                printLOG(f"Acesso negado: Nenhuma credencial fornecida. IP: {ip}", nivel="ERROR")
            return authenticate()

        elif not check_auth(auth.username, auth.password):
            if request.path == "/":
                printLOG(f"Acesso negado: Credenciais inválidas. IP: {ip} | Usuário informado: {auth.username} | Senha informada: {auth.password}", nivel="ERROR")
            return authenticate()
        if request.endpoint not in ('exibir_logs', 'get_logs'):
            printLOG(f"Acesso autorizado: Usuário '{auth.username}' | IP: {ip}", nivel="WARN")
        return f(*args, **kwargs)
    return decorated



# Códigos ANSI para cores
COLORS = {
    'RESET' : '\033[0m',
    'INFO'  : '\033[94m',  # azul claro
    'WARN'  : '\033[93m',  # amarelo
    'ERROR' : '\033[91m',  # vermelho
    'DEBUG' : '\033[90m',  # cinza
}

def printLOG(texto: str = "", nivel: str = "INFO"):
    """
    Imprime no stdout uma mensagem de log formatada:
      [YYYY-MM-DD HH:MM:SS] [NÍVEL] texto

    `nivel` pode ser: INFO, WARN, ERROR, DEBUG (case‑sensitive).
    """
    now = datetime.now()
    color = COLORS.get(nivel, COLORS['RESET'])
    reset = COLORS['RESET']

    msg = f"[{now}] [{nivel}] {texto}"
    # se quiser cor:
    print(f"{color}{msg}{reset}", file=sys.stdout)
    salvar_log_system(f"[{nivel}] {texto}")
    # Salvar histórico

#=====================================================================================

_debounce_interval  = 5.0  # segundos
_lock               = Lock()
# Agora o dicionário mapeia de debounce_key → timestamp
_ultimo_log_por_key = {}

def salvar_log_acesso(entry):
    """
    Salva entry em HISTORICO_PATH, mas:
     - se a mesma “chave” (início do entry) foi salva há menos de 5 s, ignora;
     - caso contrário, grava e atualiza o timestamp dessa chave.
    """
    try:
        # 1) Serializa com chaves ordenadas
        entry_str = json.dumps(entry, ensure_ascii=False, sort_keys=True)
        
        # 2) Extrai a parte fixa como chave para debounce
        #    Aqui usamos tudo até o primeiro espaço; ajuste para ',' ou outro
        #    delimitador se fizer mais sentido.
        debounce_key = entry_str.split(maxsplit=1)[0]

        agora = time.time()
        with _lock:
            last = _ultimo_log_por_key.get(debounce_key)
            if last is not None and (agora - last) < _debounce_interval:
                # Já gravamos essa “chave” recentemente → ignora
                return

        # 3) Grava no arquivo
        with open(HISTORICO_PATH, 'a', encoding='utf-8') as f:
            f.write(entry_str + '\n')

        # 4) Só após gravar com sucesso, atualiza o timestamp
        with _lock:
            _ultimo_log_por_key[debounce_key] = agora


        # TAMBEM GRAVA NAS LOGS
        # 1) Garante que o diretório exista
        pasta = os.path.dirname(LOG_PATH)
        if pasta and not os.path.isdir(pasta):
            os.makedirs(pasta, exist_ok=True)

        # 2) Prepara a linha com timestamp
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        linha = f"{ts} — {entry}\n"

        # 3) Abre, escreve, e força flush+sync
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(linha)
            f.flush()
            os.fsync(f.fileno())
        # ==========================================================
    except Exception as e:
        printLOG(f"Erro ao salvar histórico: {e}", nivel="ERROR")

#=====================================================================================

def salvar_log_system(entry: str) -> bool:
    """
    Salva uma linha de log no HISTORICO_PATH.
    Retorna True se salvou com sucesso, False caso contrário.
    """
    try:
        # 1) Garante que o diretório exista
        pasta = os.path.dirname(LOG_PATH)
        if pasta and not os.path.isdir(pasta):
            os.makedirs(pasta, exist_ok=True)

        # 2) Prepara a linha com timestamp
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        linha = f"{ts} — {entry}\n"

        # 3) Abre, escreve, e força flush+sync
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(linha)
            f.flush()
            os.fsync(f.fileno())

        # 4) Confirmação opcional (console)
        #print(f"[DEBUG] Log gravado: {linha.strip()}")
        return True

    except Exception:
        err = traceback.format_exc()
        # Se você tiver um printLOG, mantenha; mas garanta que o stack trace apareça
        print(f"[ERROR] Erro ao salvar histórico:\n{err}")
        return False
    

def handle_sigint(signal_received, frame):
    """
    Handler para SIGINT (Ctrl+C). 
    """

    printLOG("\n[WARN] Sistema encerrado com Ctrl+C. Encerrando o servidor...", nivel="WARN")
    os._exit(0)  # termina o processo imediatamente

# Registra o handler para SIGINT
signal.signal(signal.SIGINT, handle_sigint)

#=====================================================================================

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Não precisa ser acessível, é só para descobrir o IP da interface de saída
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

printLOG(f"SERVIDOR INICIADO EM:{get_local_ip()}", nivel="WARN")

def load_config():
    with config_lock:
        default = {
            "system_active": True,
            "system_release": False,
            "motion_detected": False
        }

        # Se não existir, cria o arquivo com o default e retorna
        if not os.path.isfile(CONFIG_PATH):
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(default, f, indent=4)
            return default

        try:
            # utf-8-sig descarta BOM de arquivos salvos com BOM
            with open(CONFIG_PATH, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            app.logger.error(f"JSON inválido em {CONFIG_PATH}: {e}. Recriando com valores default.")
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(default, f, indent=4)
            return default
        except Exception as e:
            app.logger.error(f"Erro inesperado ao carregar {CONFIG_PATH}: {e}")
            return default

def save_config(config):
    with config_lock:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)

def load_users():
    with users_lock:
        try:
            with open(USERS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            app.logger.error(f"Erro ao carregar users.json: {e}")
            return []

def save_users(users):
    with users_lock:
        try:
            with open(USERS_PATH, 'w', encoding='utf-8') as f:
                json.dump(users, f, indent=4, ensure_ascii=False)
        except Exception as e:
            app.logger.error(f"Erro ao salvar users.json: {e}")
            printLOG(f"Erro ao alvar users.json: {e}", nivel="ERROR")

def format_rfid(raw: str) -> str:
    # Remove tudo que não for hex e torna maiúsculo
    clean = re.sub(r'[^0-9A-Fa-f]', '', raw).upper()
    # Agrupa de dois em dois e junta com espaço
    return ' '.join(re.findall(r'.{1,2}', clean))

@app.route('/get_logs')
@requires_auth  # opcional, se quiser proteger também
def get_logs():
    log_path = '/home/lukas/Documents/Face-Scan-Id/Site/logs/system_log.log'
    try:
        with open(log_path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Erro ao ler o log: {str(e)}", 500


@app.route('/logs')
@requires_auth
def exibir_logs():
    return """
    <html>
    <head>
        <title>Logs do Sistema</title>
        <style>
            body {
                background-color: #f4f4f4;
                font-family: monospace;
                padding: 20px;
            }
            pre {
                background-color: #fff;
                padding: 20px;
                border: 1px solid #ccc;
                overflow-x: auto;
                white-space: pre-wrap;
                word-wrap: break-word;
                max-height: 80vh;
            }
            button {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-weight: bold;
                margin-bottom: 20px;
            }
            button:hover {
                background-color: #45a049;
            }
        </style>
    </head>
    <body>
        <h2>Logs do Sistema</h2>
        <button onclick="atualizarLogs()">Atualizar Logs</button>
        <pre id="logConteudo">Carregando logs...</pre>

        <script>
            function atualizarLogs() {
                fetch('/get_logs')
                    .then(response => {
                        if (!response.ok) {
                            throw new Error("Erro ao buscar logs");
                        }
                        return response.text();
                    })
                    .then(data => {
                        document.getElementById('logConteudo').textContent = data;
                    })
                    .catch(error => {
                        document.getElementById('logConteudo').textContent = 'Erro ao carregar logs: ' + error;
                    });
            }

            // Atualiza automaticamente ao abrir a página
            atualizarLogs();
        </script>
    </body>
    </html>
    """



@app.route('/set_stream_mode', methods=['POST'])
def set_stream_mode():
    global gerarstream
    modo = request.form.get('modo')

    if modo == 'on':
        gerarstream = True
    elif modo == 'off':
        gerarstream = False

    return 'OK'


@app.route('/historico', methods=['GET'])
def get_historico():
    try:
        historico = []
        with open(HISTORICO_PATH, 'r', encoding='utf-8') as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    historico.append(json.loads(linha))
        return jsonify(historico[::-1]), 200  # últimos primeiro
    except FileNotFoundError:
        return jsonify([]), 200
    except Exception as e:
        printLOG(f"Erro ao carregar histórico: {e}", nivel="ERROR")
        return jsonify({"error": "Erro ao carregar histórico"}), 500


@app.route('/users', methods=['GET'])
def list_users():
    return jsonify(load_users()), 200

@app.route('/users/<int:user_id>/toggle', methods=['PATCH'])
def toggle_user(user_id):
    users = load_users()
    for u in users:
        if u['id'] == user_id:
            u['nome'] 
            u['ativo'] = not u.get('ativo', True)
            usuario_nome = u.get('nome', '<sem-nome>')
            status = 'ativo' if u['ativo'] else 'inativo'
            printLOG(f"Usuário toggled: ID={user_id}, Nome={usuario_nome}, Novo status={status}", nivel="INFO")
            break
    save_users(users)
    return jsonify({'status':'ok'}), 200


def start_reconhecimento_async():
    thread = threading.Thread(target=iniciar_reconhecimento)
    thread.daemon = True
    thread.start()

def gerar_stream():
    global gerarstream
    while gerarstream:
        frame = None
        #start_reconhecimento_async()  # possível fonte de erro
        #frame = iniciar_reconhecimento()
        
        future = executor.submit(iniciar_reconhecimento)
        frame = future.result()

        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            break

@app.route('/video')
def video():
    return Response(gerar_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')



camera_base = None   # ex: "http://10.0.1.101:81"
camera_stream = None # ex: camera_base + "/stream"
ip_camera = None  # Variável global
porta_camera = 81
intervalo_ip = ("10.0.1.", 100, 200)
endpoint_camera = "/stream"

# Verifica se IP está vivo e respondendo com MJPEG
def is_ip_alive(ip, port):
    try:
        url = f"http://{ip}:{port}{endpoint_camera}"
        r = requests.get(url, stream=True, timeout=2)
        content_type = r.headers.get('Content-Type', '')
        return r.status_code == 200 and "multipart/x-mixed-replace" in content_type
    except:
        return False
salvar_log_acesso

# Faz a varredura na rede para encontrar a câmera
@app.route('/findcam')
def find_camera_wifi(ip_base=".".join(get_local_ip().split(".")[:3]) + ".", port=81, endpoint="/stream", start_ip=100, max_ip=200):
    global camera_base, camera_stream, camera_base_led, ip_camera
    printLOG("Buscando câmera na rede...",nivel="WARN")
    try:
        for i in range(start_ip, max_ip + 1):
            ip = f"{ip_base}{i}"
            if is_ip_alive(ip, port):
                camera_ip = ip
                camera_base = f"http://{ip}:{port}"
                camera_base_led = f"http://{ip}"
                camera_stream = camera_base + endpoint
                config_camera.camera_url = camera_stream

                printLOG(f"✅ Câmera encontrada: base={camera_base}, stream={camera_stream}",nivel="WARN")
                print(f"✅ Câmera encontrada: base={camera_base}, stream={camera_stream}")
                
                ip_camera = ip
                return jsonify({
                    'camera_ip': camera_ip,
                    'camera_base': camera_base,
                    'camera_stream': camera_stream
                }), 200
        printLOG(f"Câmera não encontrada.", nivel="ERROR")
        return jsonify({'error': 'Câmera não encontrada'}), 404
    except Exception as e:
        print("❌ Erro na rota /findcam:", e)
        printLOG(f"Câmera não encontrada.", nivel="ERROR")
        return jsonify({'error': 'Erro interno no servidor'}), 500

def fetch_camera_stream():
    global camera_stream
    try:
        resp = requests.get(camera_stream, stream=True, timeout=(10, None))
        resp.raise_for_status()
        return resp
    except Exception as e:
        app.logger.error(f"Não consegui conectar na câmera: {e}")
        return None



@app.route('/cam')
def cam_proxy():
    cam = fetch_camera_stream()
    if not cam:
        return jsonify({"error": "não consegui conectar à câmera"}), 502

    content_type = cam.headers.get("Content-Type","")
    boundary = content_type.split("boundary=")[1] if "boundary=" in content_type else "frame"
    mimetype = f"multipart/x-mixed-replace;boundary={boundary}"
    led_off()

    def generate():
        for chunk in cam.iter_content(chunk_size=4096):
            if chunk:
                yield chunk

    return Response(stream_with_context(generate()), mimetype=mimetype)


def proxy_camera(path: str):
    global camera_base_led
    try:
        url = f"{camera_base_led}{path}"
        r = requests.get(url, timeout=10)
        return jsonify({'status': r.status_code}), r.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 502

@app.route('/led/on', methods=['GET'])
def led_on():
    printLOG(f"Led da camera ligado.", nivel="WARN")
    return proxy_camera('/led/on')

@app.route('/led/off', methods=['GET'])
def led_off():
    printLOG(f"Led da camera desligado.", nivel="WARN")
    return proxy_camera('/led/off')


@app.route('/')
@requires_auth
def index():
    global ip_camera
    users = load_users()
    local_ip = get_local_ip()
    return render_template("index.html",
                           users=users,
                           camera_base=ip_camera,
                           ip_server=local_ip)


@app.route('/toggle', methods=['POST'])
def toggle_system():
    global ip_camera
    config = load_config()

    current = config.get('system_active', True)
    novo_estado = not current

    config['system_active'] = novo_estado

    # Se desativou, também desativa o release
    if not novo_estado:
        config['system_release'] = False
        led_off()

    save_config(config)
    printLOG(f"Sistema {'Ativado' if novo_estado else 'Desativado'} manualmente.", nivel="INFO")

    return jsonify({'ativo': novo_estado}), 200


@app.route('/status')
def status():
    config = load_config()
    return jsonify({
        'ativo': config['system_active'],
        'release': config['system_release'],
        'motion': config['motion_detected']
    })


@app.route('/add_user', methods=['POST'])
def add_user():
    users = load_users()

    nome = request.form.get('nome')
    rfid = request.form.get('rfid')
    format_rfid(rfid)
    classe = request.form.get('classe', 'PADRAO').upper()
    printLOG(f"Dados recebidos para novo usuário: Nome={nome}, RFID={rfid}, Classe={classe}", nivel="DEBUG")

    if any(u['rfid'].upper() == rfid.upper() for u in users):
        printLOG(f"add_user: RFID já cadastrado ({rfid})", nivel="WARN")
        return jsonify({"error": "RFID já cadastrado"}), 409

    # Validação simples
    if not nome or not rfid:
        printLOG("add_user: faltou nome ou rfid", nivel="ERROR")
        return jsonify({"error": "Nome e RFID são obrigatórios"}), 400

    # Datas para visitantes
    if classe == 'CONV':
        inicio = request.form.get('inicio', '-')
        fim = request.form.get('fim', '-')
    else:
        inicio = '-'
        fim = '-'

    # Gera um novo id incremental (assumindo que o último id seja o maior)
    if users:
        new_id = max(user.get('id', 0) for user in users) + 1
    else:
        new_id = 1

    novo_usuario = {
        "id": new_id,
        "nome": nome,
        "rfid": rfid,
        "classe": classe,
        "inicio": inicio,
        "fim": fim,
        "ativo": True  # padrão ativo
    }

    users.append(novo_usuario)
    save_users(users)
    printLOG(f"Usuário adicionado: ID={new_id}, Nome={nome}, Classe={classe}", nivel="INFO")
    return jsonify({"msg": "Usuário adicionado", "user": novo_usuario}), 201


@app.route('/users/<int:user_id>/update_time', methods=['PATCH'])
def update_user_time(user_id):
    users = load_users()
    user = next((u for u in users if u['id'] == user_id), None)
    
    if not user:
        printLOG(f"update_user_time: usuário ID={user_id} não encontrado", nivel="ERROR")
        return jsonify({"error": "Usuário não encontrado"}), 404

    if user['classe'] != 'CONV':
        printLOG(f"update_user_time: usuário ID={user_id} não é CONV", nivel="WARN")
        return jsonify({"error": "Somente convidados podem ter tempo editado"}), 400

    data = request.get_json()
    inicio = data.get('inicio')
    fim = data.get('fim')

    # Validação simples do formato da data/hora (YYYY-MM-DDTHH:MM)
    from datetime import datetime

    try:
        inicio_dt = datetime.strptime(inicio, '%Y-%m-%dT%H:%M')
        fim_dt = datetime.strptime(fim, '%Y-%m-%dT%H:%M')
    except Exception:
        printLOG(f"update_user_time: formato inválido ({inicio}, {fim})", nivel="ERROR")
        return jsonify({"error": "Formato inválido para data/hora. Use YYYY-MM-DDTHH:MM"}), 400

    if fim_dt <= inicio_dt:
        printLOG(f"update_user_time: fim <= inicio ({inicio} >= {fim})", nivel="ERROR")
        return jsonify({"error": "Data de fim deve ser maior que a data de início"}), 400

    # Atualiza e salva
    user['inicio'] = inicio
    user['fim'] = fim
    save_users(users)

    printLOG(f"Tempo atualizado: ID={user_id}, Nome={user['nome']}, Início={inicio}, Fim={fim}", nivel="INFO")
    return jsonify({"msg": "Tempo atualizado", "user": user}), 200



@app.route('/delete_user/<int:user_id>', methods=['POST'])
@requires_auth
def delete_user(user_id):
    users = load_users()

    # captura nome antes de remover
    user = next((u for u in users if u['id'] == user_id), None)
    if not user:
        printLOG(f"delete_user: usuário ID={user_id} não encontrado", nivel="ERROR")
        return jsonify({"error": "Usuário não encontrado"}), 404

    usuario_nome = user['nome']
    usuario_rfid = user.get('rfid', '<sem-rfid>')

    users = [u for u in users if u['id'] != user_id]
    save_users(users)

    printLOG(f"Usuário removido: ID={user_id}, Nome={usuario_nome}, RFID={usuario_rfid}", nivel="INFO")
    return redirect(url_for('index'))

# Novo endpoint para liberação remota
@app.route('/liberar', methods=['POST'])
def liberar_post():
    config = load_config()

    if not config['system_active']:
        config['system_release'] = False
        save_config(config)
        printLOG("Erro ao agendar a Liberação, o sistema está desativado.",nivel="ERROR")
        return jsonify({"msg": "O sistema está desativado"}), 200

    config['system_release'] = True
    save_config(config)
    printLOG("Liberação agendada",nivel="WARN")
    return jsonify({"msg": "Liberação agendada", "ativo": True}), 200


@app.route('/liberar', methods=['GET'])
def liberar_get():
    global last_time
    config = load_config()

    if not config['system_active']:
        last_time = datetime.now().isoformat(sep=' ', timespec='seconds')
        return jsonify({"access": "denied", "reason": "Sistema desativado"}), 200

    access = "allowed" if config['system_release'] else "denied"
    if access == "allowed" and config['system_release'] and config['system_active']:
        config['system_release'] = False
        printLOG("Acesso liberado.",nivel="WARN")
    return jsonify({"access": access}), 200

@app.route('/release/reset', methods=['POST'])
def reset_release():
    config = load_config()
    # responde com o novo estado
    if config['system_release']:
        printLOG("Liberação cancelada.",nivel="WARN")
    else:
        printLOG("Não tem liberação agendada.",nivel="ERROR")

    # zera o flag
    config['system_release'] = False
    save_config(config)

    return jsonify({'release': config['system_release']}), 200


# Endpoint para sinal de movimento

# Guarda o instante da última detecção
last_motion_time = None
MOTION_TIMEOUT = 3  # segundos que o movimento permanece 'True'

@app.route('/movimento', methods=['POST'])
def movimento_post():
    global last_motion_time
    last_motion_time = datetime.now()

    # se já não estava verdadeiro, atualiza o config
    cfg = load_config()
    if not cfg.get('motion_detected', False):
        cfg['motion_detected'] = True
        #cfg['system_release'] = False

    cfg['system_release'] = False
    save_config(cfg)
    printLOG("Movimento Detectado!", nivel="WARN")
    return jsonify({'movimento': True}), 200

@app.route('/movimento', methods=['GET'])
def movimento_get():
    global last_motion_time

    cfg = load_config()
    now = datetime.now()
    ativo = False

    # se já houve um POST recente
    if last_motion_time:
        delta = (now - last_motion_time).total_seconds()
        if delta < MOTION_TIMEOUT:
            ativo = True

    # se o estado mudou em relação ao config, atualiza o arquivo
    if ativo != cfg.get('motion_detected', False):
        cfg['motion_detected'] = ativo
        save_config(cfg)

    return jsonify({'movimento': ativo}), 200



# Variáveis de controle para o debounce
ultimo_nome_facial = None
ultima_hora_facial = None
DEBOUNCE_FACIAL_SEGUNDOS = 7

@app.route('/reconhecimento', methods=['POST'])
def reconhecimento_facial_post():
    global last_uid, last_user, last_time, last_access, last_reason
    global ultimo_nome_facial, ultima_hora_facial

    data = request.get_json(force=True)
    nome = data.get('nome', 'DESCONHECIDO')
    sucesso = data.get('sucesso', False)

    agora = datetime.now()

    # Debounce: evita múltiplas detecções do mesmo nome em menos de X segundos
    if (
        sucesso and 
        nome == ultimo_nome_facial and 
        ultima_hora_facial and 
        (agora - ultima_hora_facial) < timedelta(seconds=DEBOUNCE_FACIAL_SEGUNDOS)
    ):
        return jsonify({"status": "ignored", "motivo": "debounce"}), 200

    # Atualiza o controle do debounce
    if sucesso:
        ultimo_nome_facial = nome
        ultima_hora_facial = agora

    #hora_str = agora.isoformat(sep=' ', timespec='seconds')
    hora_str = agora.strftime("%d/%m/%Y %H:%M:%S")

    # Atualiza globais
    last_uid     = "FACIAL"
    last_time    = hora_str
    last_access  = "allowed" if sucesso else "denied"
    last_reason  = ""
    last_user    = { "nome": nome } if sucesso else None

    if last_user == "Estranho" or not last_user:
        last_reason = "Ouve um erro inesperado ao capturar o nome"

    # Salva no log
    salvar_log_acesso({
        "uid": "FACIAL",
        "nome": nome,
        "status": last_access,
        "hora": hora_str,
    })

    return jsonify({"status": last_access}), 200



@app.route('/biometria-log', methods=['POST'])
def biometria_log():
    global last_uid, last_user, last_time, last_access, last_reason

    agora = datetime.now()

    data = request.get_json(force=True)

    nome = data.get('nome', 'DESCONHECIDO')
    sucesso = data.get('sucesso', False)

    hora_str = datetime.now().isoformat(sep=' ', timespec='seconds')
    hora_str = agora.strftime("%d/%m/%Y %H:%M:%S")
    
    # Atualiza globais para GET /rfid
    last_uid     = "BIOMETRIA"
    last_time    = hora_str
    last_access  = "allowed" if sucesso else "denied"
    last_reason  = ""
    last_user    = { "nome": nome } if sucesso else None

    # Salva no log
    salvar_log_acesso({
        "uid": "BIOMETRIA",
        "nome": nome,
        "status": last_access,
        "hora": hora_str,
        "motivo": last_reason
    })

    return '', 204



# Endpoints para ESP32 via /rfid

# @app.route('/rfid', methods=['GET'])
# def health():
#     return jsonify({"status": "ok"}), 200

# no topo do arquivo, junto dos outros globals:
last_uid     = None
last_user    = None
last_time    = None
last_access  = None
last_reason  = None

# POST /rfid: recebe o cartão, decide allow/deny, preenche todos os globals
@app.route('/rfid', methods=['POST'])
def rfid_post():
    global last_uid, last_user, last_time, last_access, last_reason, agora

    agora = datetime.now()

    cfg = load_config()
    data = request.get_json(force=True)
    raw_uid = data.get('uid','').strip()

    hora_str = agora.strftime("%d/%m/%Y %H:%M:%S")

    # 1) Formata o UID
    incoming = format_rfid(raw_uid)
    last_uid  = incoming
    last_time = hora_str

    # 2) Procura o usuário correspondente
    users = load_users()
    matched = next((u for u in users if format_rfid(u.get('rfid','')) == incoming), None)
    last_user = matched  # grava o usuário (ou None)

    # inicializa campos de acesso
    last_access = 'denied'
    last_reason = ''

    # 3) Sistema desligado? (mas o last_user já foi populado)
    if not cfg['system_active']:
        # Se for ADM, libera mesmo com sistema desativado
        if matched and matched.get('classe') == 'ADM':
            last_access = 'allowed'
            salvar_log_acesso({
                "uid": last_uid,
                "nome": matched.get('nome'),
                "status": last_access,
                "hora": last_time,
                "motivo": 'ADM com sistema desligado'
            })
            return jsonify({'access': 'allowed', 'user': matched}), 200

        last_reason = 'Sistema desativado'
        salvar_log_acesso({
            "uid": last_uid,
            "nome": matched['nome'] if matched else 'DESCONHECIDO',
            "status": last_access,
            "hora": last_time,
            "motivo": last_reason
        })
        return jsonify({'access':'denied','reason':last_reason}), 200

    # 4) Cartão não cadastrado?
    if not matched:
        last_reason = 'Usuário não encontrado'
        salvar_log_acesso({
            "uid": last_uid,
            "nome": matched['nome'] if matched else 'DESCONHECIDO',
            "status": last_access,
            "hora": last_time
            #"motivo": last_reason
        })
        return jsonify({'access':'denied','reason':'Usuario nao encontrado'}), 200

    # 5) Usuário inativo?
    if not matched.get('ativo', True):
        last_reason = 'Usuário desativado'
        salvar_log_acesso({
            "uid": last_uid,
            "nome": matched['nome'] if matched else 'DESCONHECIDO',
            "status": last_access,
            "hora": last_time,
            "motivo": last_reason
        })
        return jsonify({'access':'denied','reason':'User OFF'}), 200

    # 6) Convidado fora do período?
    if matched.get('classe') == 'CONV':
        try:
            ini = datetime.fromisoformat(matched['inicio'])
            fim = datetime.fromisoformat(matched['fim'])
        except Exception:
            last_reason = 'Erro no formato de data'
            salvar_log_acesso({
                "uid": last_uid,
                "nome": matched['nome'] if matched else 'DESCONHECIDO',
                "status": last_access,
                "hora": last_time,
                "motivo": last_reason
            })
            return jsonify({'access':'denied','reason':last_reason}), 200

        if not (ini <= datetime.now() <= fim):
            last_reason = 'Fora do período permitido'
            salvar_log_acesso({
                "uid": last_uid,
                "nome": matched['nome'] if matched else 'DESCONHECIDO',
                "status": last_access,
                "hora": last_time,
                "motivo": last_reason
            })
            return jsonify({'access':'denied','reason':'Fora do periodo permitido'}), 200

    # 7) Tudo OK: libera acesso
    last_access = 'allowed'
    # Salvar histórico
    salvar_log_acesso({
        "uid": last_uid,
        "nome": matched.get('nome'),
        "status": last_access,
        "hora": last_time
    })
    return jsonify({'access':'allowed','user':matched}), 200


# GET /rfid: retorna o último evento, depois limpa
@app.route('/rfid', methods=['GET'])
def rfid_get():
    global last_uid, last_user, last_time, last_access, last_reason

    # sem nada no buffer, devolve 204
    if not last_uid:
        return '', 204

    payload = {
        "uid":     last_uid,
        "time":    last_time,
        "access":  last_access,
    }
    if last_user:
        payload["user"] = last_user
    if last_access == 'denied':
        payload["reason"] = last_reason

    # apaga tudo antes de devolver
    reset_last()
    return jsonify(payload), 200


def reset_last():
    """Limpa o buffer de última leitura."""
    global last_uid, last_user, last_time, last_access, last_reason
    last_uid     = None
    last_user    = None
    last_time    = None
    last_access  = None
    last_reason  = None


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
