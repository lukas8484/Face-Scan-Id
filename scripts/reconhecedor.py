from ast import While
import cv2
from datetime import datetime
from collections import deque, Counter
from colorama import init, Fore
import os
import time
import tkinter
from tkinter import Tk, Label, IntVar, ttk, Entry, Button, messagebox
import socket
import threading
import cv2
from pyzbar.pyzbar import decode
import qrcode
import json
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


camera_index = None
ip_url_text = ""
run = False
running = False

def is_ip_alive(ip, port):
    import socket
    try:
        with socket.create_connection((ip, port), timeout=0.4):
            return True
    except:
        return False

#def find_camera_wifi(ip_base="10.0.0.", port="4747", endpoint="/video", start_ip=100, max_ip=200):
def find_camera_wifi(ip_base="10.0.1.", port="81", endpoint="/stream", start_ip=100, max_ip=200):
    start_ip -= 1
    global camera_index, ip_url_text, root, running, run, ip

    def buscar():
        global camera_index, ip_url_text, running, run, ip

        # Reset estados
        running = True
        camera_index = None
        run = False
        progress['value'] = 0
        btn_buscar.config(state="disabled")
        btn_fechar.config(state="normal")

        print("Procurando câmera IP na rede...")
        for i in range(start_ip, max_ip + 1):
            if not running:
                print("Busca cancelada pelo usuário.")
                break

            ip = f"{ip_base}{i}"
            ip_url = f"http://{ip}:{port}{endpoint}"
            ip_url_text = ip_url

            label.config(text=ip_url_text)

            if is_ip_alive(ip, int(port)):
                print(f"IP ativo encontrado: {ip_url}")
                time.sleep(1.2)

                for tentativa in range(2):
                    cap = cv2.VideoCapture(ip_url)
                    if cap.isOpened():
                        cap.release()
                        print(f"Câmera IP válida encontrada: {ip_url}")
                        camera_index = ip_url
                        run = True
                        running = False
                        root.after(0, root.destroy)
                        return
                    cap.release()
                    print(f"Tentativa {tentativa+1} falhou para {ip_url}")
                    time.sleep(5.5)
                
            if i >= max_ip:
                temp_root = Tk()
                temp_root.withdraw()
                messagebox.showerror("Erro", "Nenhuma câmera WIFI encontrada.")
                temp_root.destroy()

            try:
                progress['value'] = ((i - start_ip + 1) / (max_ip - start_ip + 1)) * 100
            except:
                break
            root.update_idletasks()
            print(f"{ip_url}")
            time.sleep(0.1)

        print("Busca finalizada sem sucesso.")
        btn_buscar.config(state="normal")
        running = False

    def on_closing():
        global running
        running = False
        root.destroy()

    def iniciar_busca():
        threading.Thread(target=buscar, daemon=True).start()

    root = Tk()
    root.title("Procurando...")

    label = Label(root, text="Iniciando busca...")
    label.pack(pady=10)

    progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
    progress.pack(pady=10)
    progress.pack(padx=20)

    btn_buscar = Button(root, text="Procurar novamente", command=iniciar_busca)
    btn_buscar.pack(pady=5)

    btn_fechar = Button(root, text="Fechar", command=on_closing)
    btn_fechar.pack(pady=5)

    root.protocol("WM_DELETE_WINDOW", on_closing)

    iniciar_busca()  # faz a primeira busca ao abrir
    root.mainloop()

    return camera_index if camera_index else -1

def find_camera(max_index=16):
    print("Procurando câmera USB conectada...")
    
    for index in range(max_index + 1):
        print(f"Tentativa no índice {index}")
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            cap.release()
            return index
        cap.release()

    return -1

# Use a função find_camera() para encontrar o índice da câmera conectada
camera_index = find_camera()
#camera_index = 1

# INDIQUE MANUALMENTE UM HTTP PARA CAPTURA DE IMAGEM.
#camera_index = "http://10.0.1.103:81/stream"
#camera_index = "http://10.0.0.169:4747/video"
#camera_index = "http://10.0.1.151:4747/video"
#camera_index = "http://10.0.1.101:81/stream"

if camera_index != -1:
    print(f"Câmera conectada encontrada no índice {camera_index}")
    run = True
else:
    print("Nenhuma câmera encontrada até o índice 16.")
    run = False
    temp_root = Tk()
    temp_root.withdraw()
    messagebox.showerror("Erro", "Nenhuma câmera USB encontrada.")
    temp_root.destroy()

    temp_root = Tk()
    temp_root.withdraw()
    find_cam_wifi = messagebox.askyesno("Confirmação", "Deseja procurar câmeras disponíveis na sua rede?")
    temp_root.destroy()

    if find_cam_wifi:
        try:
            camera_index = find_camera_wifi()
            if camera_index != -1:
                messagebox.showinfo("Sucesso", f"Câmera Wi-Fi encontrada!        \n\nIP: {ip} \nLINK: {ip_url_text}    ")
                run = True
            else:
                raise Exception("Nenhuma câmera IP encontrada.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao encontrar câmera Wi-Fi: {e}")
            run = False
    else:
        run = False

# Inicializar colorama
init()

# Função para carregar IDs e nomes
def load_id_names(filename):
    id_names = {}
    with open(filename, 'r') as file:
        for line in file:
            id, name = line.strip().split(',')
            id_names[int(id)] = name
    return id_names

# Caminho dos modelosa
model_path = 'modelos/'

# Caminho haarcascade
detectorFace = cv2.CascadeClassifier('cascade/haarcascade_frontalface_default.xml')
upper_cascade = cv2.CascadeClassifier('cascade/haarcascade_upperbody.xml')
eye_cascade_path = cv2.CascadeClassifier('cascade/haarcascade_eye.xml')

# Instanciando LBPH Faces Recognizer
recognizer = cv2.face.LBPHFaceRecognizer_create() #type: ignore
recognizer.read("classifier/classificadorLBPH.yml")

# Modelos para idade e gênero
faceProto = model_path + "opencv_face_detector.pbtxt"
faceModel = model_path + "opencv_face_detector_uint8.pb"
ageProto = model_path + "age_deploy.prototxt"
ageModel = model_path + "age_net.caffemodel"
genderProto = model_path + "gender_deploy.prototxt"
genderModel = model_path + "gender_net.caffemodel"

MODEL_MEAN_VALUES = (78.4263377603, 87.7689143744, 114.895847746)
ageList = ['(0-2 anos)', '(4-6 anos)', '(8-12 anos)', '(15-20 anos)', '(25-30 anos)',
           '(30-37 anos)', '(38-42 anos)', '(48-53 anos)', '(60-70 anos)']
genderList = ['Homem', 'Mulher']

faceNet = cv2.dnn.readNet(faceModel, faceProto) #type ignore
ageNet = cv2.dnn.readNet(ageModel, ageProto) #type ignore
genderNet = cv2.dnn.readNet(genderModel, genderProto) #type ignore

height, width = 220, 220
font = cv2.FONT_HERSHEY_COMPLEX_SMALL
camera = cv2.VideoCapture(camera_index)

# Limiar de confiança
# 30 - EXTREMAMENTE PRECISO
# 40 - MUITO PRECISO
# 50 - MEDIO PRECISO
# 60 - POUCO PRECISO
# 70 - NADA PRECISO

# Limiar de confiança
limiar_confianca = 50

# Carregar IDs e nomes
id_names = load_id_names('info.txt')

# Dicionário para rastrear IDs de faces
face_ids = {}

# Dicionário para rastrear previsões de gênero e idade
face_info = {}

# Variáveis para armazenar o último log registrado
last_log = {}

# Próximo ID a ser atribuído
next_id = 1
unknown_id = 00
next_unknown_id = 1

# Dicionário para rastrear IDs de corpos
body_ids = {}
next_body_id = 1

# Dicionário para rastrear IDs e nomes dos corpos
body_names = {}

# Dicionário para rastrear IDs de corpos e associar com rostos
body_face_mapping = {}

# Variável de filtro
frames_to_confirm = 500  # Ajuste este valor para mais precisão ou reatividade

# Criar pasta para armazenar imagens de desconhecidos
if not os.path.exists('estranhos'):
    os.makedirs('estranhos')

# Função para calcular a média móvel ponderada
def weighted_moving_average(values, alpha=0.6):
    avg = 0
    for i in range(len(values)):
        avg = alpha * values[i] + (1 - alpha) * avg
    return avg

# Contador de imagens para cada desconhecido
unknown_counters = {}

tempo_inicio_piscadas = None
acesso = "Negado"
first_read = False
piscou = False
piscou_vezes = 0
eyes_cont = 0
olhos_abertos_anterior = True
verificacao_concluida = False
tempo_verificacao = 0

# Remover IDs inativos (Faces e Corpos)
def remove_inactive_ids(active_ids, id_dict, info_dict=None, mapping_dict=None):
    for id in list(id_dict.keys()):
        if id not in active_ids:
            del id_dict[id]
            if info_dict is not None and id in info_dict:
                del info_dict[id]
            if mapping_dict is not None and id in mapping_dict:
                del mapping_dict[id]

# Lista de IDs ativos
active_face_ids = []
active_body_ids = []

def draw_text_center(
    img, 
    text, 
    y=None, 
    color=(0, 255, 255), 
    font=cv2.FONT_HERSHEY_TRIPLEX, 
    font_scale=1, 
    thickness=2, 
    background_color=None, 
    padding=10
):
    """
    Desenha um texto centralizado horizontalmente (e opcionalmente verticalmente) na imagem.
    Pode incluir um fundo atrás do texto.

    Parâmetros:
        img: imagem onde o texto será desenhado
        text: texto a ser exibido
        y: posição vertical (se None, centraliza verticalmente)
        color: cor do texto (BGR)
        font: fonte do texto
        font_scale: escala da fonte
        thickness: espessura da fonte
        background_color: cor de fundo (BGR) ou None para sem fundo
        padding: espaço em volta do texto no fundo (em pixels)
    """
    text_size, baseline = cv2.getTextSize(text, font, font_scale, thickness)
    text_width, text_height = text_size

    x = (img.shape[1] - text_width) // 2
    if y is None:
        y = (img.shape[0] + text_height) // 2

    if background_color is not None:
        top_left = (x - padding, y - text_height - padding)
        bottom_right = (x + text_width + padding, y + baseline + padding)
        cv2.rectangle(img, top_left, bottom_right, background_color, -1)

    cv2.putText(img, text, (x, y), font, font_scale, color, thickness)



# Carrega o banco de dados dos usuários
def carregar_usuarios(caminho_json):
    with open(caminho_json, 'r', encoding='utf-8') as f:
        return json.load(f)

# Busca um usuário pelo RFID
def buscar_usuario_por_rfid(rfid, usuarios):
    for usuario in usuarios:
        if usuario["rfid"].upper() == rfid.upper():
            return usuario
    return None

def criar_qrcode(lista_de_textos):
    for texto in lista_de_textos:
        # Criar o objeto QRCode com configurações personalizadas
        qr = qrcode.QRCode(  # type: ignore
            version=9,
            error_correction=qrcode.constants.ERROR_CORRECT_H,  # type: ignore
            box_size=10,
            border=4
        )

        # Adiciona os dados e gera o QR Code
        qr.add_data(texto)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # Salvar a imagem
        nome_arquivo = f"qrcode_{texto}.png"
        img.save(f"QRCODE/{nome_arquivo}")

        # Carregar e exibir com OpenCV
        imagem_cv = cv2.imread(f"QRCODE/{nome_arquivo}")
        if imagem_cv is not None:
            cv2.imshow(f"QR Code: {texto}", imagem_cv)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        else:
            print(f"Erro ao carregar {nome_arquivo}.")

# Leitura do QR Code pela webcam
def ler_qrcode_e_verificar_usuarios(conectado, imagem, caminho_json):
    usuarios = carregar_usuarios(caminho_json)

    while True:

        qrcodes = decode(imagem)
        for qr in qrcodes:

            dados = qr.data.decode('utf-8').strip()
            tipo = qr.type
            retangulo = qr.rect

            # Desenha um retângulo ao redor do QR Code
            x, y, w, h = retangulo
            cv2.rectangle(imagem, (x, y), (x + w, y + h), (0, 255, 0), 2)

            print(f"📦 Tipo: {tipo}")
            print(f"📄 Dados lidos: {dados}")

            usuario = buscar_usuario_por_rfid(dados, usuarios)
            if usuario:

                print(f"✅ Usuário encontrado:")
                print(f"🔹 Nome: {usuario['nome']}")
                print(f"🔹 RFID: {usuario['rfid']}")
                print(f"🔹 Classe: {usuario['classe']}")
                print(f"🔹 Acesso: {usuario['acesso']}")
                print(f"🔹 ID: {usuario['id']}")

                return True

                #criar_qrcode({usuario['rfid']})
                
            else:
                print("❌ RFID não encontrado na base de dados.")
                return False

            # Espera 2 segundos após a leitura para evitar leituras repetidas
            cv2.imshow('Leitor de QR Code', imagem)
            cv2.waitKey(2000)
            time.sleep(3)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()




start_main = True
ja_run = False
increment = 0

if run:
    os.system('clear')

    while True:
        conectado, imagem = camera.read()
        if not conectado or imagem is None:
            print("Erro ao capturar imagem. Verifique a conexão.")
            #messagebox.showerror("Erro", "Falha ao capturar imagem. Verifique a conexão.")
            camera.release()
            cv2.destroyAllWindows()
            start_main = False

            print("Tentando reconectar...")
            #messagebox.showinfo("Tentativa", "Tentando reconectar...")
            for tentativa in range(10):
                cap = cv2.VideoCapture(camera_index)
                time.sleep(1)
                if cap.isOpened():
                    camera = cap  # substitui o objeto da câmera
                    print(f"Câmera reconectada: {camera_index}")
                    #messagebox.showinfo("Sucesso", "Câmera reconectada.")
                    run = True
                    start_main = True
                    break  # sai do loop de tentativa

                print(f"Tentativa {tentativa + 1} falhou para {camera_index}")
                camera.release()
                cv2.destroyAllWindows()
                time.sleep(5+tentativa)

            if not start_main:
                messagebox.showerror("Erro", "Falha ao reconectar a camera. Verifique a conexão.")
                break

        if start_main:
            pass
        
            conectado, imagem = camera.read()
            if conectado:
                imagem = cv2.resize(imagem, (640, 480))
                imagem = cv2.flip(imagem, 1) # INVERTE A IMAGEM HORIZONTALMENTE PARA PARECER MAIS NATURAL.

                imageGray = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)

                # Detecção da face baseado no haarcascade
                faceDetect = detectorFace.detectMultiScale(
                    imageGray,
                    scaleFactor=1.2,   # Ajuste o fator de escala conforme necessário
                    minNeighbors=7,     # Ajuste o número mínimo de vizinhos conforme necessário
                    minSize=(70, 70),   # Ajuste o tamanho mínimo do objeto conforme necessário
                    flags=cv2.CASCADE_SCALE_IMAGE
                )

                # Ajustar parâmetros para detectar corpos maiores
                upper = upper_cascade.detectMultiScale(
                    imageGray,
                    scaleFactor=1.0080,
                    minNeighbors=3,
                    minSize=(30, 90),
                    maxSize=(300, 500)
                )

                # Atualizar lista de IDs ativos (Faces)
                for (x, y, w, h) in faceDetect:
                    face_image = cv2.resize(imageGray[y:y+h, x:x+w], (width, height))
                    id, confianca = recognizer.predict(face_image)
                    active_face_ids.append(id)
                    face_ids[id] = (x, y, w, h)

                    cv2.rectangle(imagem, (5, 5), (200, 40), (0, 0, 0), -1)  # Fundo preto para melhor visibilidade
                    cv2.putText(imagem, f"Acesso: {acesso}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                    if acesso == "Liberado":
                                cv2.rectangle(imagem, (240, 5), (200, 40), (0, 255, 0), -1) # Verde para liberado
                    elif acesso == "Negado":
                                cv2.rectangle(imagem, (240, 5), (200, 40), (0, 0, 255), -1) # Vermelho para negado        

                # Desenhar corpos
                for (x, y, w, h) in upper:

                    found_body_match = False
                    acesso = "Negado"
                    piscou = False
                    piscou_vezes = 0
                    verificacao_concluida = False
                    olhos_abertos_anterior = True

                    for body_id, (prev_x, prev_y, prev_w, prev_h) in body_ids.items():
                        overlap_x = max(0, min(x + w, prev_x + prev_w) - max(x, prev_x))
                        overlap_y = max(0, min(y + h, prev_y + prev_h) - max(y, prev_y))
                        overlap_area = overlap_x * overlap_y

                        if not overlap_area > 0:
                            # O corpo ainda está na cena
                            found_body_match = False
                            body_names[body_id] = 'Estranho'  # Inicializar o nome como desconhecido
                            body_face_mapping[body_id] = None  # Associar ID do corpo ao rosto (inicialmente None)
                            acesso = "Negado"
                            piscou = False
                            piscou_vezes = 0
                            verificacao_concluida = False
                            olhos_abertos_anterior = True
                            break
                        

                        if overlap_area > 0:
                            # O corpo ainda está na cena
                            body_ids[body_id] = (x, y, w, h)
                            found_body_match = True
                            break

                    if not found_body_match:
                        body_id = next_body_id
                        body_ids[body_id] = (x, y, w, h)
                        next_body_id += 1
                        if body_id not in body_names:
                            body_names[body_id] = 'Estranho'  # Inicializar o nome como desconhecido
                            body_face_mapping[body_id] = None  # Associar ID do corpo ao rosto (inicialmente None)
                            acesso = "Negado"
                            piscou = False
                            piscou_vezes = 0
                            verificacao_concluida = False
                            olhos_abertos_anterior = True

                    # Verificar rosto dentro do retângulo do corpo
                    face_detected = False
                    for (fx, fy, fw, fh) in faceDetect:
                        if fx >= x and fy >= y and fx + fw <= x + w and fy + fh <= y + h:
                            # O rosto está dentro do retângulo do corpo
                            face_image = cv2.resize(imageGray[fy:fy+fh, fx:fx+fw], (width, height))
                            id, confianca = recognizer.predict(face_image)
                            if confianca <= limiar_confianca:
                                person_name = id_names.get(id, 'Estranho')
                                acesso = "Negado"
                                piscou = False
                                piscou_vezes = 0
                                olhos_abertos_anterior = True
                                if body_face_mapping[body_id] is None or body_face_mapping[body_id] == id:
                                    body_names[body_id] = person_name  # Associar o nome ao corpo
                                    body_face_mapping[body_id] = id  # Associar o rosto ao ID do corpo
                                    face_detected = True

                                    if piscou == True and piscou_vezes >= 5:
                                        acesso = "Liberado"
                                break

                    # Se nenhum rosto foi detectado dentro do retângulo
                    if not face_detected:
                        
                        if body_id not in body_face_mapping or body_face_mapping[body_id] is None:
                            # Apenas resetar o nome se o corpo não tiver um nome associado
                            body_names[body_id] = 'Estranho'
                            acesso = "Negado"
                            piscou = False
                            piscou_vezes = 0
                            verificacao_concluida = False
                            olhos_abertos_anterior = True
                            body_face_mapping[body_id] = None

                    # Desenhar retângulo e texto
                    cv2.rectangle(imagem, (x, y), (x + w, y + h + 200), (255, 255, 255), 2)
                    body_text = f"{body_names.get(body_id, 'Estranho')}"
                    cv2.putText(imagem, body_text, (x, y - 10), font, 1, (255, 255, 255), 1, cv2.LINE_AA)

                # Remover IDs inativos (Corpos)
                active_body_ids = []
                # Atualizar lista de IDs ativos (Corpos)
                for (x, y, w, h) in upper:
                    found_body_match = False
                    for body_id, (prev_x, prev_y, prev_w, prev_h) in body_ids.items():
                        overlap_x = max(0, min(x + w, prev_x + prev_w) - max(x, prev_x))
                        overlap_y = max(0, min(y + h, prev_y + prev_h) - max(y, prev_y))
                        overlap_area = overlap_x * overlap_y
                        if overlap_area > 0:
                            body_ids[body_id] = (x, y, w, h)
                            found_body_match = True
                            active_body_ids.append(body_id)
                            break

                    if not found_body_match:
                        body_id = next_body_id
                        body_ids[body_id] = (x, y, w, h)
                        next_body_id += 1
                        active_body_ids.append(body_id)
                        acesso = "Negado"
                        piscou = False
                        piscou_vezes = 0
                        verificacao_concluida = False
                        olhos_abertos_anterior = True

                # Remover IDs inativos de faces e corpos
                remove_inactive_ids(active_face_ids, face_ids, face_info)
                remove_inactive_ids(active_body_ids, body_ids, body_names, body_face_mapping)

                # Verificar quais IDs não estão ativos
                for face_id in list(face_ids.keys()):
                    if face_id not in active_face_ids:
                        # Remover face inativa
                        del face_ids[face_id]
                        if face_id in face_info:
                            del face_info[face_id]


                # Remove faces que não estão mais ativas
                for face_id in list(face_ids.keys()):
                    if face_id not in active_face_ids:
                        del face_ids[face_id]
                        face_info.pop(face_id, None)


                # Associar IDs a novas faces detectadas
                for (x, y, w, h) in faceDetect:
                    face_image = cv2.resize(imageGray[y:y+h, x:x+w], (width, height))
                    
                    # Fazendo comparação da imagem detectada
                    id, confianca = recognizer.predict(face_image)
                    
                    # Convertendo confiança para porcentagem
                    confianca_pct = 100 - confianca

                    # Verificar se a face é conhecida baseada na confiança
                    if confianca <= limiar_confianca:
                        name = id_names.get(id, 'Estranho')
                        
                        if id == -1:
                            id = 0  # Define o ID do desconhecido como 0 na saída do log
                            confianca_pct = 0
                        log_color = Fore.GREEN  # Verde para conhecido
                        rectangle_color = (0, 255, 0)  # Verde para conhecido

                        # Lógica de detectar piscadas para verificação
                        faces = faceDetect
                        if len(faces) > 0:
                            eyes_cont = 0
                            for (x, y, w, h) in faces:
                                roi_face = imageGray[y:y + h, x:x + w]
                                roi_face_clr = imagem[y:y + h, x:x + w]

                                # Corta a região do rosto da metade pra cima
                                metade_altura = h // 2
                                roi_olhos = roi_face[0:metade_altura, :]
                                roi_olhos_clr = roi_face_clr[0:metade_altura, :]

                                eyes = eye_cascade_path.detectMultiScale(roi_olhos, 1.1, 7, minSize=(50, 50))


                                for (ex, ey, ew, eh) in eyes:
                                    cv2.rectangle(roi_face_clr, (ex, ey), (ex + ew, ey + eh), (255, 255, 255), 2)
                                    eyes_cont += 1

                                olhos_abertos = len(eyes) >= 2

                                if not verificacao_concluida:
                                    # Se já começou a contar piscadas e passou o tempo limite
                                    if tempo_inicio_piscadas and (time.time() - tempo_inicio_piscadas > 2):
                                        piscou_vezes = 0
                                        tempo_inicio_piscadas = None
                                        cv2.putText(imagem, "TEMPO ESGOTADO", (70, 140),cv2.FONT_HERSHEY_TRIPLEX, 1, (0, 0, 255), 2)

                                    if olhos_abertos:
                                        if not olhos_abertos_anterior:
                                            piscou_vezes += 1

                                            # Inicia o tempo na primeira piscada
                                            if piscou_vezes == 1:
                                                tempo_inicio_piscadas = time.time()

                                        if piscou_vezes < 5:
                                            draw_text_center(imagem, "PISQUE",y=50, color=(0, 255, 255), background_color=(0, 0, 0))
                                            cv2.putText(imagem, f"{piscou_vezes}", (70, 110), cv2.FONT_HERSHEY_TRIPLEX, 1, (0, 0, 255), 2)
                                        else:
                                            verificacao_concluida = True
                                            tempo_verificacao = time.time()
                                            tempo_inicio_piscadas = None  # reset
                                            acesso = "Liberado"

                                if eyes_cont < 1:
                                    draw_text_center(imagem, "CHEGUE MAIS PERTO", color=(0, 0, 255), background_color=(0, 0, 0))


                                else:
                                    if time.time() - tempo_verificacao > 2:
                                    # Após 2 segundos, reinicia a lógica
                                        #cv2.putText(imagem, "TEMPO 2 ESGOTADO", (70, 140),cv2.FONT_HERSHEY_TRIPLEX, 1, (0, 0, 255), 2)
                                        piscou_vezes = 0
                                        piscou = False
                                        verificacao_concluida = False
                                        olhos_abertos_anterior = True
                                        tempo_verificacao = time.time()
                                        acesso = "Negado"

                                olhos_abertos_anterior = olhos_abertos

                        else:
                            piscou_vezes = 0
                            verificacao_concluida = True
                            olhos_abertos_anterior = True
                            acesso = "Negado"

                    else:
                        unknown_id = "00"
                        # Verificar se já há um ID atribuído para este rosto
                        found_match = False
                        for face_id, face_data in face_ids.items():
                            if len(face_data) == 4:
                                x, y, w, h = face_data
                                face_position = (x, y, w, h)
                                (prev_x, prev_y, prev_w, prev_h) = face_position
                                overlap_x = max(0, min(x + w, prev_x + prev_w) - max(x, prev_x))
                                overlap_y = max(0, min(y + h, prev_y + prev_h) - max(y, prev_y))
                                overlap_area = overlap_x * overlap_y
                                if overlap_area > 0:
                                    face_ids[face_id] = ((x, y, w, h), face_position)
                                    id = face_id
                                    found_match = True
                                    break
                                else:
                                    print(f"Dados incompletos para face_id {face_id}: {face_data}")

                        if not found_match:
                            #Capturar estranho apenas quando a tecla K é pressionada
                            unknown_id = f"00{next_unknown_id}"
                            face_ids[unknown_id] = ((x, y, w, h), (x, y, w, h))
                            id = unknown_id
                            confianca = 0
                            next_unknown_id += 1
                        else:
                    
                            confianca = 0

                        id = "00"
                        name = 'Estranho'
                        log_color = Fore.RED  # Vermelho para desconhecido
                        rectangle_color = (0, 0, 255)  # Vermelho para desconhecido
                    
                    key = cv2.waitKey(1)

                    if key == 13:  # Capturar estranhos apenas quando a tecla K é pressionada
                        # Salvar imagem do estranho

                        #Capturar estranho apenas quando a tecla K é pressionada
                        #unknown_id = f"00{next_unknown_id}"
                        unknown_id = "00"
                        face_ids[unknown_id] = ((x, y, w, h), (x, y, w, h))
                        id = unknown_id
                        confianca = 0
                        next_unknown_id += 1
                        
                        increment += 1

                        # Recortar a face e converter para preto e branco
                        face_crop = imagem[y:y+h, x:x+w]
                        face_crop_gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)

                        output_dir = 'estranhos'
                        if not os.path.exists(output_dir):
                            os.makedirs(output_dir)

                        # Definir o nome do arquivo
                        filename = f'{output_dir}/{unknown_id}_Estranho_{increment}.jpg'

                        # Salvar a imagem em preto e branco
                        cv2.imwrite(filename, face_crop_gray)
                        print(f'Imagem do estranho salva: {filename}')


                    # Adicionar detecção de idade e gênero
                    face = imagem[max(0, y - 20):min(y + h + 20, imagem.shape[0] - 1), max(0, x - 20):min(x + w + 20, imagem.shape[1] - 1)]
                    blob = cv2.dnn.blobFromImage(face, 1.0, (227, 227), MODEL_MEAN_VALUES, swapRB=False)
                    
                    # Predição de gênero
                    genderNet.setInput(blob)
                    genderPreds = genderNet.forward()
                    gender = genderList[genderPreds[0].argmax()]
                    
                    # Predição de idade
                    ageNet.setInput(blob)
                    agePreds = ageNet.forward()
                    age = ageList[agePreds[0].argmax()]

                    # Atualizar informações de gênero e idade
                    if id not in face_info:
                        face_info[id] = {'genders': deque(maxlen=frames_to_confirm), 'ages': deque(maxlen=frames_to_confirm)}
                    
                    face_info[id]['genders'].append(gender)
                    face_info[id]['ages'].append(age)

                    # Calcular a média móvel ponderada
                    most_common_gender = weighted_moving_average([1 if g == 'Homem' else 0 for g in face_info[id]['genders']])
                    most_common_age = Counter(face_info[id]['ages']).most_common(1)[0][0]

                    # Determinar gênero com base na média ponderada
                    most_common_gender = 'Homem' if most_common_gender >= 0.5 else 'Mulher'

                    # Formatar a data e hora sem os segundos
                    current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M')

                    # Preparar a linha de log
                    log_line = {
                        'id': id,
                        'time': current_time_str,
                        'nome': name,
                        'gênero': most_common_gender,
                        'idade': most_common_age
                    }

                    # Exibir a linha de log no terminal apenas se houver alterações
                    if id not in last_log or {k: log_line[k] for k in log_line}:
                        last_log[id] = log_line
                        if log_color == Fore.GREEN:
                            if acesso == "Liberado":
                                print(f"id: {Fore.GREEN}{id}{Fore.RESET}, time: {current_time_str}, nome: {Fore.GREEN}{name}{Fore.RESET}, confiança: {int(confianca_pct)}%, gênero: {most_common_gender}, idade: {most_common_age}, acesso: {Fore.GREEN}{acesso}{Fore.RESET}")
                            elif acesso == "Negado":
                                print(f"id: {Fore.GREEN}{id}{Fore.RESET}, time: {current_time_str}, nome: {Fore.GREEN}{name}{Fore.RESET}, confiança: {int(confianca_pct)}%, gênero: {most_common_gender}, idade: {most_common_age}, acesso: {Fore.RED}{acesso}{Fore.RESET}")
                        elif log_color == Fore.RED:
                            if acesso == "Liberado":
                                print(f"id: {Fore.RED}{id}{Fore.RESET}, time: {current_time_str}, nome: {Fore.RED}{name}{Fore.RESET}, confiança: {int(confianca_pct)}%, gênero: {most_common_gender}, idade: {most_common_age}, acesso: {Fore.GREEN}{acesso}{Fore.RESET}")
                            elif acesso == "Negado":
                                print(f"id: {Fore.RED}{id}{Fore.RESET}, time: {current_time_str}, nome: {Fore.RED}{name}{Fore.RESET}, confiança: {int(confianca_pct)}%, gênero: {most_common_gender}, idade: {most_common_age}, acesso: {Fore.RED}{acesso}{Fore.RESET}")
                    # Desenhar retângulo em volta da face
                    cv2.rectangle(imagem, (x, y), (x + w, y + h), rectangle_color, 2)  # Retângulo em vermelho

                    # Definir texto a ser exibido para ID, nome e porcentagem de confiança
                    display_text = f"ID: {id}, {name}, {int(confianca_pct)}%"
                    (text_width, text_height), _ = cv2.getTextSize(display_text, font, fontScale=1, thickness=1)
                    text_x = x
                    text_y = y - 10
                    text_bg_width = text_width + 10
                    text_bg_height = text_height + 10
                    text_bg_rect = ((text_x, text_y), (text_x + text_bg_width, text_y - text_bg_height))

                    # Desenhar fundo do texto (retângulo preto)
                    cv2.rectangle(imagem, text_bg_rect[0], text_bg_rect[1], (0, 0, 0), cv2.FILLED)

                    # Desenhar texto sobre a imagem
                    cv2.putText(imagem, display_text, (text_x + 5, text_y - 5), font, 1, (255, 255, 255), 1, cv2.LINE_AA)
                    
                    # Definir posição e tamanho do fundo do texto de gênero e idade
                    gender_age_text = f'{most_common_gender}, {most_common_age}'
                    (gender_age_text_width, gender_age_text_height), _ = cv2.getTextSize(gender_age_text, font, fontScale=1, thickness=1)
                    gender_age_text_x = x
                    gender_age_text_y = y + h + 24
                    gender_age_text_bg_width = gender_age_text_width + 10
                    gender_age_text_bg_height = gender_age_text_height + 10
                    gender_age_text_bg_rect = ((gender_age_text_x, gender_age_text_y), (gender_age_text_x + gender_age_text_bg_width, gender_age_text_y - gender_age_text_bg_height))

                    # Desenhar fundo do texto de gênero e idade (retângulo preto)
                    cv2.rectangle(imagem, gender_age_text_bg_rect[0], gender_age_text_bg_rect[1], (0, 0, 0), cv2.FILLED)

                    # Desenhar texto de gênero e idade sobre a imagem
                    cv2.putText(imagem, gender_age_text, (gender_age_text_x + 5, gender_age_text_y - 5), font, 1, (255, 255, 255), 1, cv2.LINE_AA)
            if conectado:
                # Mostrando frame
                cv2.imshow("Reconhecedor", imagem)
                if cv2.waitKey(1) == ord('q'):
                    break

                # Verificar se a janela foi fechada pelo botão de fechar (X)
                if cv2.getWindowProperty('Reconhecedor', cv2.WND_PROP_VISIBLE) < 1:
                    break

camera.release()
cv2.destroyAllWindows()