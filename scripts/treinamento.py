import cv2
import os
import numpy as np
from tkinter import Tk, Label, ttk, messagebox
from colorama import init, Fore
import shutil
from collections import defaultdict

# Cria o classificador LBPH
lbph = cv2.face.LBPHFaceRecognizer_create()  # type: ignore

# Inicializar colorama
init()

os.system('clear')

# Cria diretório para salvar as informações e as fotos, se não existir
output_dir = 'fotos'
if not os.path.exists(output_dir):
    print(f"{Fore.YELLOW}Faça um cadastro primeiro.{Fore.RESET}")
    messagebox.showerror("Erro", "Faça um cadastro primeiro.")



def reorganizePhotos():
    output_dir = 'fotos'

    if not os.path.exists(output_dir):
        return

    pathsImages = sorted(
        [f for f in os.listdir(output_dir) if f.endswith(('.jpg', '.png'))],
        key=lambda x: (x.split('_')[0], x.split('_')[1], int(x.split('_')[2].split('.')[0]))
    )

    arquivos_por_usuario = defaultdict(list)

    for filename in pathsImages:
        parts = filename.split('_')
        if len(parts) < 3:
            print(f'{Fore.RED}Nome de arquivo inválido: {filename}{Fore.RESET}')
            continue
        user_key = f'{parts[0]}_{parts[1]}'  # id_nome
        arquivos_por_usuario[user_key].append(filename)

    should_reorganize = False

    for user_key, arquivos in arquivos_por_usuario.items():
        for idx, nome_arquivo in enumerate(arquivos, start=1):
            partes = nome_arquivo.split('_')
            numero = int(partes[2].split('.')[0])
            if numero != idx:
                should_reorganize = True
                break
        if should_reorganize:
            break

    if not should_reorganize:
        print(f"{Fore.GREEN}As fotos já estão numeradas corretamente. Nenhuma reorganização necessária.{Fore.RESET}")
        return

    print("Reorganizando as fotos...")

    # Cria uma pasta temporária
    temp_dir = os.path.join(output_dir, 'temp')
    os.makedirs(temp_dir, exist_ok=True)

    for user_key, arquivos in arquivos_por_usuario.items():
        id, nome = user_key.split('_')
        for idx, old_filename in enumerate(arquivos, start=1):
            ext = os.path.splitext(old_filename)[1]
            new_filename = f'{id}_{nome}_{idx}{ext}'
            shutil.move(os.path.join(output_dir, old_filename), os.path.join(temp_dir, new_filename))

    for file in os.listdir(temp_dir):
        shutil.move(os.path.join(temp_dir, file), os.path.join(output_dir, file))

    os.rmdir(temp_dir)
    print(f"{Fore.GREEN}Reorganização concluída.{Fore.RESET}")

def getImageWithId(progress, total):
    '''
    Percorre o diretório 'fotos', lê todas as imagens com CV2 e organiza
    o conjunto de faces com seus respectivos IDs, atualizando a barra de progresso.
    '''
    pathsImages = [os.path.join('fotos', f) for f in os.listdir('fotos')]
    faces = []
    ids = []

    for i, pathImage in enumerate(pathsImages):
        if pathImage.endswith('.jpg') or pathImage.endswith('.png'):  # Verifica se é um arquivo de imagem
            imageFace = cv2.cvtColor(cv2.imread(pathImage), cv2.COLOR_BGR2GRAY)
            
            # Extrai o ID a partir do nome do arquivo
            id = os.path.basename(pathImage).split('_')[0]
            print(pathImage)

            # Verifica se o ID é numérico
            if id.isdigit():
                ids.append(int(id))
                faces.append(imageFace)
                
                # Mostra a imagem sendo treinada
                cv2.imshow("Treinando...", imageFace)
                cv2.waitKey(100)  # Espera 100ms para mostrar a imagem

            # Atualiza a barra de progresso
            progress['value'] = ((i + 1) / total) * 100
            progress.update_idletasks()

    cv2.destroyAllWindows()  # Fecha todas as janelas abertas
    return np.array(ids), faces

def trainRecognizer():
    '''
    Função para treinar o classificador LBPH e salvar o modelo treinado.
    '''
    # Configura a interface do Tkinter

    reorganizePhotos()

    root = Tk()
    root.title("Treinamento de Reconhecimento Facial")
    Label(root, text="Treinando o classificador...").pack(pady=10)

    # Configura a barra de progresso
    progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
    progress.pack(pady=10)
    progress.pack(padx=20)

    # Reorganiza as fotos antes de treinar
    ###reorganizePhotos()
    if os.path.exists(output_dir):
        pathsImages = sorted(
    [f for f in os.listdir(output_dir) if f.endswith('.jpg') or f.endswith('.png')],
    key=lambda x: int(x.split('_')[2].split('.')[0])
)
        total_images = len(pathsImages)

    # Verifica se há imagens para treinar
    if os.path.exists(output_dir):
        if total_images == 0:
            print(f"{Fore.RED}Nenhuma imagem encontrada para treinamento.{Fore.RESET}")
            root.destroy()
            messagebox.showerror("Erro", f"Nenhuma imagem encontrada para treinamento.")
            return

    # Obtém os IDs e faces das imagens
    if os.path.exists(output_dir):
        ids, faces = getImageWithId(progress, total_images)

    # Treina o classificador LBPH com as faces e IDs obtidos
    if os.path.exists(output_dir):
        lbph.train(faces, ids)

    # Salva o classificador treinado em um arquivo
    lbph.write('classifier/classificadorLBPH.yml')
    print(f'{Fore.GREEN}Treinamento concluído com sucesso!{Fore.RESET}')
    root.destroy()
    messagebox.showinfo("Sucesso", "Treinamento concluído com sucesso!")

# Chamada da função para iniciar o treinamento
if os.path.exists(output_dir):
    trainRecognizer()
