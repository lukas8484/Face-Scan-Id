import os
import shutil
import re
import os
import re
import numpy as np
import time
import subprocess
from colorama import init, Fore
from tkinter import Tk, Label, IntVar, ttk, Entry, Button, messagebox

# Inicializar colorama
init()

os.system('clear')

def iniciar_aprimoramento():
    pasta_origem = 'estranhos'  # Pasta contendo as imagens desconhecidas
    pasta_destino = 'fotos'  # Pasta para mover as imagens renomeadas

    if not os.path.exists(pasta_destino):
        os.makedirs(pasta_destino)

    os.system('clear')
    id_estranho = id_estranho_entry.get()
    id_cadastrado = id_user_entry.get()
    nome = nome_entry.get()

    renomear_e_mover_imagens(pasta_origem, pasta_destino, id_estranho, id_cadastrado, nome)
    
    treinar = messagebox.askyesno("Confirmação", f"Deseja executar um treinamento ?")
    if treinar:
            
        """Executa o script de treinamento do modelo."""
        try:
            subprocess.run(["python3", "/home/lukas/Documents/Face-Scan-Id/scripts/treinamento.py"])
            root.destroy()
            messagebox.showinfo("Sucesso", "Usuário aprimorado e treinado com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao treinar o modelo: {e}")
    else:
        root.destroy()
        messagebox.showinfo("Sucesso", "Usuário aprimorado com sucesso!")

def fechar():
    exit()

# Criar janela Tkinter para entrada de ID e Nome
root = Tk()
root.title("Aprimorar Usuário")
root.geometry("300x240")

Label(root, text="ID do estranho:").pack()
id_estranho_entry = Entry(root)
id_estranho_entry.pack()

Label(root, text="ID do usuário:").pack()
id_user_entry = Entry(root)
id_user_entry.pack()

Label(root, text="Nome atribuído:").pack()
nome_entry = Entry(root)
nome_entry.pack()

Button(root, text="Iniciar Aprimoramento", command=iniciar_aprimoramento).pack(pady=10)

Button(root, text="Fechar", command=fechar).pack(pady=5) 

def obter_ultimo_numero_imagem(pasta_destino, id_cadastrado, nome):
    padrao = re.compile(rf'{id_cadastrado}_{nome}_(\d+).jpg')
    max_numero = 0
    for nome_arquivo in os.listdir(pasta_destino):
        correspondencia = padrao.match(nome_arquivo)
        if correspondencia:
            num = int(correspondencia.group(1))
            if num > max_numero:
                max_numero = num
    return max_numero

def verificar_id_cadastrado(info_file_path, id_cadastrado, nome):
    id_cadastrado = int(id_cadastrado)
    nome = nome.strip()  # Remover espaços em branco extras do nome
    
    id_cadastrado_existe = False
    id_encontrado = False
    nome_encontrado = False
    id_nome_encontrado = False

    if os.path.exists(info_file_path):
        with open(info_file_path, 'r') as file:
            for line in file:
                existing_id, existing_name = line.strip().split(',')
                existing_id = int(existing_id)

                if existing_id == id_cadastrado:
                    id_encontrado = True
                if existing_name == nome:
                    nome_encontrado = True
                if existing_id == id_cadastrado and existing_name == nome:
                    id_nome_encontrado = True
                    break  # já achou os dois, pode parar

    # Verificações depois de ler tudo
    if id_nome_encontrado:
        id_cadastrado_existe = True
    elif id_encontrado and not nome_encontrado:
        messagebox.showerror("Erro", "Nome não cadastrado.")
        root.destroy()
    elif nome_encontrado and not id_encontrado:
        messagebox.showerror("Erro", "ID não cadastrado.")
        root.destroy()
    else:
        messagebox.showerror("Erro", "ID e nome não cadastrados.")
        root.destroy()
        return id_cadastrado_existe

def adicionar_id_info(info_file_path, id_cadastrado, nome):
    with open(info_file_path, 'a') as info_file:
        info_file.write(f'{id_cadastrado},{nome}\n')
    print(f'ID {id_cadastrado} adicionado com sucesso ao arquivo info.txt.')

def renomear_e_mover_imagens(pasta_origem, pasta_destino, id_estranho, id_cadastrado, nome):
    info_file_path = 'info.txt'
    id_cadastrado_existe = verificar_id_cadastrado(info_file_path, id_cadastrado, nome)

    #if not id_cadastrado_existe:
        #messagebox.showerror(f"Erro", f"O id:{id_user_entry.get()} não está cadastrado")
        #adicionar_id_info(info_file_path, id_cadastrado, nome)
        #root.destroy()

    ultimo_numero = obter_ultimo_numero_imagem(pasta_destino, id_cadastrado, nome)

    for nome_arquivo in os.listdir(pasta_origem):
        if nome_arquivo.startswith(id_estranho) and nome_arquivo.endswith('.jpg'):
            ultimo_numero += 1
            novo_nome_arquivo = f'{id_cadastrado}_{nome}_{ultimo_numero}.jpg'
            caminho_origem = os.path.join(pasta_origem, nome_arquivo)
            caminho_destino = os.path.join(pasta_destino, novo_nome_arquivo)

            # Mover o arquivo
            shutil.move(caminho_origem, caminho_destino)
            print(f'Movido: {nome_arquivo} para {novo_nome_arquivo}')

    print(f'Todas as imagens do estranho {id_estranho_entry.get()} movidas e renomeadas para o ID cadastrado {id_cadastrado} ({nome}).')

root.mainloop()
