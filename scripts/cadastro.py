import cv2
import os
import re
import numpy as np
import time
import subprocess
from colorama import init, Fore
import tkinter
from tkinter import Tk, Label, IntVar, ttk, Entry, Button, messagebox
import socket
import threading

# Inicializar colorama
init()

# Caminho Haarcascade
face_cascade_path = 'cascade/haarcascade_frontalface_default.xml'
eye_cascade_path = 'cascade/haarcascade-eye.xml'

# Classificador baseado nos Haarcascade
face_cascade = cv2.CascadeClassifier(face_cascade_path)
eye_cascade = cv2.CascadeClassifier(eye_cascade_path)

run = False
id = 0
nome = ""
completou_cadastro = False
output_dir_temp = []

os.system('clear')

def is_ip_alive(ip, port):
    import socket
    try:
        with socket.create_connection((ip, port), timeout=0.2):
            return True
    except:
        return False

def find_camera_wifi(ip_base="10.0.0.", port="4747", endpoint="/video", start_ip=100, max_ip=200):
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

                for tentativa in range(3):
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
                    time.sleep(0.5)
                
            if i >= max_ip:
                temp_root = Tk()
                temp_root.withdraw()
                messagebox.showerror("Erro", "Nenhuma câmera USB encontrada.")
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
                messagebox.showinfo("Sucesso", f"Câmera Wi-Fi encontrada com sucesso! \nIP: {ip} \nLINK: {ip_url_text}")
                run = True
            else:
                raise Exception("Nenhuma câmera IP encontrada.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao encontrar câmera Wi-Fi: {e}")
            run = False
    else:
        run = False

def iniciar_captura():
    global id, nome, run
    id = id_entry.get()
    nome = nome_entry.get()
    root.destroy()
    run = True

# Numero de Amostras:
# 20 - NADA PRECISO 
# 40 - POUCO PRECISO
# 60 - MEDIO PRECISO
# 80 - MUITO PRECISO
# 100 - EXTREMAMENTE PRECISO

increment = 1
numMostras = 30 #Numero de Amostras
foto_num = numMostras
width, height = 220, 220
min_de_luz = 100
camera = cv2.VideoCapture(camera_index)

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


# Função para atualizar a barra de progresso
def atualizar_barra(increment, numMostras, progress_var, progress_label):
    progress = int((increment / numMostras) * 100)
    progress_var.set(progress)
    progress_label.config(text=f"Progresso: {progress}% ({increment}/{numMostras})")
    root.update_idletasks()

def obter_ultimo_numero_imagem(output_dir, id, nome):
    padrao = re.compile(rf'{id}_{nome}_(\d+).jpg')
    max_numero = 0
    for nome_arquivo in os.listdir(output_dir):
        correspondencia = padrao.match(nome_arquivo)
        if correspondencia:
            num = int(correspondencia.group(1))
            if num > max_numero:
                max_numero = num
    return max_numero

def fechar():
    exit()
    
if run:

    conectado, imagem = camera.read()
    if not conectado or imagem is None:
        print("Erro ao capturar imagem. Verifique a conexão")
        messagebox.showerror("Erro", " Falha ao capturar imagem. Verifique a conexão")
        exit()

    # Criar janela Tkinter para entrada de ID e Nome
    root = Tk()
    root.title("Cadastro de Usuário")
    root.geometry("300x200")

    Label(root, text="Digite seu ID:").pack()
    id_entry = Entry(root)
    id_entry.pack()

    Label(root, text="Digite seu Nome:").pack()
    nome_entry = Entry(root)
    nome_entry.pack()

    Button(root, text="Iniciar Captura", command=iniciar_captura).pack(pady=10)

    # Atalho para Enter
    root.bind('<Return>', lambda event: iniciar_captura())

    Button(root, text="Fechar", command=fechar).pack(pady=5) 
    root.mainloop()

    output_dir = 'fotos'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    info_file_path = 'info.txt'
    existing_ids = {}
    if os.path.exists(info_file_path):
        with open(info_file_path, 'r') as file:
            for line in file:
                existing_id, existing_name = line.strip().split(',')
                existing_ids[int(existing_id)] = existing_name

    if nome == '' or not nome.isalpha() or id == 0 or id.isalpha():
        print(f'{Fore.RED}Erro:{Fore.RESET} Digite um id e um nome válido.')
        time.sleep(2)
        messagebox.showerror("Erro", f"Digite um id e um nome válido.")
        adicionar_no_info = False
        run = False

    if int(id) in existing_ids:
        if existing_ids[int(id)] == nome:
            print(f'{Fore.YELLOW}ID {id} já cadastrado com o nome {nome}. Atualizando as fotos...{Fore.RESET}')
            adicionar_no_info = False  # ✅ não vamos adicionar novamente
            run = True
        else:
            print(f'{Fore.RED}Erro:{Fore.RESET} ID {id} já cadastrado com o nome {existing_ids[int(id)]}. Use um ID diferente.')
            time.sleep(2)
            messagebox.showerror("Erro", f"ID {id} já cadastrado com o nome {existing_ids[int(id)]}. Use um ID diferente.")
            adicionar_no_info = False
            run = False
    else:
        adicionar_no_info = True  # ✅ é um novo ID, podemos adicionar

    completou_cadastro = False
    print(f'{Fore.LIGHTWHITE_EX}Capturando as faces...{Fore.RESET}')
    
    root = Tk()
    root.title("Progresso de Captura de Fotos")
    root.geometry("400x150")
    
    progress_var = IntVar()
    progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate", variable=progress_var)
    progress_bar.pack(pady=20)
    
    progress_label = Label(root, text=f"Progresso: 0% (0/{numMostras})")
    progress_label.pack()
    
    while increment <= numMostras:

        conectado, imagem = camera.read()
        if not conectado or imagem is None:
            print("Erro ao capturar imagem. Verifique a conexão")
            messagebox.showerror("Erro", " Falha ao capturar imagem. Verifique a conexão")
            break 

        ret, frame = camera.read()
        frame = cv2.resize(frame, (640, 480))
        frame = cv2.flip(frame, 1) # INVERTE A IMAGEM HORIZONTALMENTE PARA PARECER MAIS NATURAL.
        frame_gui = frame.copy()

        draw_text_center(frame_gui, "Encaixe o rosto aqui",y=50, color=(255, 255, 255), background_color=(0, 0, 0))

        text = f"Faltam: {foto_num} "
        (font_width, font_height), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)

        frame_height, frame_width = frame_gui.shape[:2]

        # Margem da borda
        margin = 10

        # Posição do texto e do fundo
        x_text = frame_width - font_width - margin
        y_text = 30

        # Retângulo de fundo colado à borda direita
        cv2.rectangle(frame_gui, (x_text - 5, 5), (frame_width - margin, 40), (0, 0, 0), -1)
        cv2.putText(frame_gui, text, (x_text, y_text), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)


        altura, largura = frame_gui.shape[:2]
        centro = (largura // 2, altura // 2)

        # Tamanho do oval (metade do eixo maior e menor)
        eixo_maior = largura // 5
        eixo_menor = altura // 3

        # Desenha um oval amarelo (BGR: 0, 255, 255)
        cv2.ellipse(frame_gui, centro, (eixo_maior, eixo_menor), 0, 0, 360, (0, 255, 255), 2)

        if not ret:
            print("Falha na captura de imagem")
            messagebox.showerror("Erro", "Falha na captura de imagem")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.5, minSize=(35, 35), flags=cv2.CASCADE_SCALE_IMAGE)

        if increment < numMostras+1 and increment != 0:
            for (x, y, w, h) in faces:
                cv2.rectangle(frame_gui, (x, y), (x+w, y+h), (0, 0, 255), 2)
                face_region = frame[y:y + h, x:x + w]
                face_region_gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
                eyes = eye_cascade.detectMultiScale(face_region_gray)
                luz = np.average(gray)

                cv2.rectangle(frame_gui, (5, 5), (150, 40), (0, 0, 0), -1)  # Fundo preto para melhor visibilidade
                cv2.putText(frame_gui, f"Luz: {luz:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

                # Coordenadas do rosto detectado
                face_center_x = x + w // 2
                face_center_y = y + h // 2

                # Centro da elipse (já calculado anteriormente)
                elipse_cx = largura // 2
                elipse_cy = altura // 2

                # Semi-eixos da elipse (já definidos)
                a = eixo_maior
                b = eixo_menor

                tolerancia = -120  # Tolerância ao redor do centro da elipse, em pixels

                # Verificando se o centro do rosto está dentro de uma "zona de tolerância" ao redor do centro da elipse
                in_ellipse = ((face_center_x - elipse_cx)**2 / (a + tolerancia)**2) + ((face_center_y - elipse_cy)**2 / (b + tolerancia)**2) <= 1


                if len(eyes) == 2 and luz < min_de_luz:
                    print(f"{Fore.RED}Baixa luminosidade!{Fore.RESET}")
                    
                if luz < min_de_luz:
                    texto = "POUCA LUZ!"
                    (text_width, text_height), _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, 2, 5)
                    text_x = (frame_gui.shape[1] - text_width) // 2
                    text_y = (frame_gui.shape[0] + text_height) // 2
                    cv2.putText(frame_gui, texto, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 5)

                ultimo_numero = obter_ultimo_numero_imagem(output_dir, id, nome)

                if len(eyes) == 2 and luz > min_de_luz:
                    
                    if in_ellipse:
                        
                        face_off = cv2.resize(gray[y:y + h, x:x + w], (width, height))
                        output_dir_temp.append((face_off.copy(), f"{id}_{nome}_{ultimo_numero+increment}.jpg"))  # copia a imagem e salva nome
                        print(f'{Fore.GREEN}[Foto {increment} capturada com sucesso] - Qualidade da luz: {luz:.2f}{Fore.RESET}')
                        foto_num -= 1
                        increment += 1
                        atualizar_barra(increment, numMostras, progress_var, progress_label)
                        time.sleep(1)
                    else:
                        draw_text_center(frame_gui, "FORA DE CENTRO", color=(0, 0, 255), background_color=(0, 0, 0))
        
        cv2.imshow('Cadastro', frame_gui)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        # Verificar se a janela foi fechada pelo botão de fechar (X)
        if cv2.getWindowProperty('Cadastro', cv2.WND_PROP_VISIBLE) < 1:
            run = False
            break

    if increment >= numMostras:
        print(f'{Fore.BLUE}Fotos capturadas com sucesso!{Fore.RESET}')
        completou_cadastro = True
        increment = 0

    if adicionar_no_info and completou_cadastro:
        with open(info_file_path, 'a') as info_file:
            info_file.write(f'{id},{nome}\n')

    if completou_cadastro:
        for img, nome in output_dir_temp:
            cv2.imwrite(os.path.join(output_dir, nome), img)

        cv2.destroyAllWindows()
        
        treinar = messagebox.askyesno("Confirmação", f"Deseja executar um treinamento ?")
        if treinar:
                
            """Executa o script de treinamento do modelo."""
            try:
                subprocess.run(["python3", "/home/lukas/Documents/Face-Scan-Id/scripts/treinamento.py"])
                root.destroy()
                messagebox.showinfo("Sucesso", "Usuário cadastrado e treinado com sucesso!")
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao treinar o modelo: {e}")
        else:
            root.destroy()
            messagebox.showinfo("Sucesso", "Usuário cadastrado com sucesso!")


    root.destroy()
    camera.release()
    cv2.destroyAllWindows()