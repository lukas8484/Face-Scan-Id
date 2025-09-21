import tkinter as tk
from tkinter import LEFT, ttk, messagebox, Toplevel
from PIL import Image, ImageTk
import os
import subprocess
import time

#from numpy import PINF, size

class FaceRecognitionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Reconhecimento Facial")
        self.root.geometry("500x300")
        
        self.create_menu()
        self.create_widgets()

    def create_menu(self):
        """Cria o menu superior."""
        menu_bar = tk.Menu(self.root)
        opcoes_menu = tk.Menu(menu_bar, tearoff=0)
        opcoes_menu.add_command(label="Cadastrar Faces", command=self.cadastrar_faces)
        opcoes_menu.add_command(label="Treinar Modelo", command=self.treinar_modelo)
        opcoes_menu.add_command(label="Reconhecer Faces", command=self.reconhecer_faces)
        opcoes_menu.add_command(label="Aprimorar", command=self.aprimorar_modelo)
        opcoes_menu.add_separator()
        opcoes_menu.add_command(label="Ver Fotos Cadastradas", command=self.ver_fotos)
        opcoes_menu.add_command(label="Sair", command=self.root.quit)
        menu_bar.add_cascade(label="Opções", menu=opcoes_menu)
        self.root.config(menu=menu_bar)

    def ver_fotos(self):
        self.visualizador = VisualizadorFotos(self.root, "fotos")

    def create_widgets(self):
        """Cria os botões e elementos da interface."""
        titulo = tk.Label(self.root, text="Sistema de Reconhecimento Facial", font=("Arial", 16))
        titulo.pack(pady=20)

        btn_cadastrar = ttk.Button(self.root, text="Cadastrar Faces", command=self.cadastrar_faces)
        btn_cadastrar.pack(pady=10)

        btn_treinar = ttk.Button(self.root, text="Treinar Modelo", command=self.treinar_modelo)
        btn_treinar.pack(pady=10)

        btn_reconhecer = ttk.Button(self.root, text="Reconhecer Faces", command=self.reconhecer_faces)
        btn_reconhecer.pack(pady=10)

        btn_fechar = ttk.Button(self.root, text="Sair", command=self.root.quit)
        btn_fechar.pack(pady=10)

    def cadastrar_faces(self):
        try:
            subprocess.run(["python3", "/home/lukas/Documents/Face-Scan-Id/scripts/cadastro.py"])
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao executar o cadastro: {e}")

    def treinar_modelo(self):
        """Executa o script de treinamento do modelo."""
        try:
            subprocess.run(["python3", "/home/lukas/Documents/Face-Scan-Id/scripts/treinamento.py"])
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao treinar o modelo: {e}")

    def reconhecer_faces(self):
        """Executa o script de reconhecimento facial."""
        try:
            subprocess.run(["python3", "/home/lukas/Documents/Face-Scan-Id/scripts/reconhecedor.py"])
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao reconhecer faces: {e}")

    def aprimorar_modelo(self):
        """Executa o script de aprimoramento do modelo."""
        try:
            subprocess.run(["python3", "/home/lukas/Documents/Face-Scan-Id/scripts/aprimoramento.py"])
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao aprimorar o modelo: {e}")

class VisualizadorFotos:
    def __init__(self, root, pasta_fotos='fotos'):
        self.root = tk.Toplevel(root)
        self.root.title("Fotos Cadastradas")
        self.root.geometry("760x700")
        self.fotos_dir = pasta_fotos
        self.fotos = self.carregar_fotos()
        self.criar_interface()
    
    def carregar_fotos(self):
        return [f for f in os.listdir(self.fotos_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
    
    def criar_interface(self):

        # Canvas com a barra de rolagem
        self.canvas = tk.Canvas(self.root)
        self.scrollbar = ttk.Scrollbar(self.root, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        # Botão de deletar
        self.botao_deletar = ttk.Button(self.canvas, text="Deletar foto", command=self.deletar_foto)
        self.botao_deletar.pack(side=tk.TOP, anchor='e', padx=10, pady=5)  # Alinhado à esquerda

        # Botão de deletar
        self.botao_deletar = ttk.Button(self.canvas, text="Deletar usuario", command=self.deletar_usuario)
        self.botao_deletar.pack(side=tk.TOP, anchor='e', padx=10, pady=5)  # Alinhado à esquerda

        # Botão para fechar a janela, logo abaixo
        self.botao_fechar = ttk.Button(self.canvas, text="Fechar", command=self.root.destroy)
        self.botao_fechar.pack(side=tk.TOP, anchor='e', padx=10, pady=5)  # Alinhado à esquerda

        # Para centralizar verticalmente os botões
        self.canvas.pack_propagate(False)  # Para que o canvas não se redimensione automaticamente

        # Vincula o evento de mudança no tamanho do conteúdo para ajustar a rolagem
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        # Cria a janela dentro do canvas para adicionar o conteúdo rolável
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Configura a rolagem do canvas
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Adiciona a barra de rolagem e o canvas à janela
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Carregar as miniaturas das fotos
        self.carregar_thumbnails()

    def carregar_thumbnails(self):
        
        # Verifique se o diretório existe
        if not os.path.exists(self.fotos_dir):
            messagebox.showerror("Erro", "O diretório de fotos não existe.")
            return

        fotos = os.listdir(self.fotos_dir)
        
        # Filtra apenas os arquivos de fotos com extensões válidas
        fotos = [f for f in fotos if f.endswith(('.jpg', '.png', '.jpeg', '.PNG'))]

        if not fotos:
            messagebox.showinfo("Sem Fotos", "Não há fotos cadastradas.")
            return

        notebook = ttk.Notebook(self.scrollable_frame)
        notebook.pack(fill='both', expand=True,)  # Deixe espaço para o botão

        # Dicionário para armazenar as fotos por ID
        usuarios = {}

        # Organiza as fotos por ID
        for foto in fotos:
            try:
                # Extrai o ID e o nome da foto
                nome, ext = os.path.splitext(foto)
                id_usuario, nome_usuario, num_foto = nome.split('_')

                # Se o ID não estiver no dicionário, cria uma nova lista
                if id_usuario not in usuarios:
                    usuarios[id_usuario] = {'nome': nome_usuario, 'fotos': []}

                # Adiciona a foto na lista do usuário
                usuarios[id_usuario]['fotos'].append(foto)
            except ValueError:
                # Em caso de erro no formato do nome, pode ser uma foto corrompida ou fora do padrão
                continue

        # Cria uma aba para cada usuário
        for id_usuario, dados_usuario in usuarios.items():
            aba_usuario = ttk.Frame(notebook)
            notebook.add(aba_usuario, text=f"ID: {id_usuario} - Nome: {dados_usuario['nome']} ({len(dados_usuario['fotos'])} fotos)")

            # Exibe o nome e ID do usuário
            try:
                nome_id_label = tk.Label(aba_usuario, text=f"ID: {id_usuario} - Nome: {dados_usuario['nome']} ({len(dados_usuario['fotos'])} fotos)", font=("Arial", 14))
            except Exception as e:
                print(f"Erro ao criar o label: {e}")

            nome_id_label = tk.Label(aba_usuario, text=f"ID: {id_usuario} - Nome: {dados_usuario['nome']} ({len(dados_usuario['fotos'])} fotos)", font=("Arial", 14))
            nome_id_label.grid(row=0, column=0, pady=10, padx=10)

            # Exibe as fotos do usuário
            for idx, foto in enumerate(dados_usuario['fotos']):
                img_path = os.path.join(self.fotos_dir, foto)
                try:
                    img = Image.open(img_path)
                    img = img.resize((100, 100))  # Ajuste o tamanho da imagem
                    img_tk = ImageTk.PhotoImage(img)
                    
                    # Exibe a imagem com evento de clique
                    label_img = tk.Label(aba_usuario, image=img_tk, cursor="hand2")
                    label_img.image = img_tk  # Manter referência à imagem #type: ignore
                    label_img.grid(row=(idx // 4), column=idx % 4, padx=5, pady=5, sticky="nsew")
                    label_img.bind("<Button-1>", lambda event, foto=foto: self.selecionar_foto(foto))
                except Exception as e:
                    messagebox.showerror("Erro", f"Erro ao carregar a foto {foto}: {e}")
    
    def exibir_imagem_ampliada(self, caminho):
        # Fecha a janela anterior, se existir
        if hasattr(self, 'janela_ampliada') and self.janela_ampliada.winfo_exists():
            self.janela_ampliada.destroy()

        # Cria nova janela
        self.janela_ampliada = Toplevel(self.root)
        self.janela_ampliada.title("Visualização Ampliada")

        imagem = Image.open(caminho)
        img_tk = ImageTk.PhotoImage(imagem)
        lbl = tk.Label(self.janela_ampliada, image=img_tk)
        lbl.image = img_tk  # Mantém referência #type: ignore
        lbl.pack()


    def selecionar_foto(self, foto):
        self.foto_selecionada = foto
        self.exibir_imagem_ampliada("fotos/" + self.foto_selecionada)
        print(f"Foto selecionada: {self.foto_selecionada}")  # Debug
        self.botao_deletar.config(state="normal")  # Ativa o botão de deletar

        
    def deletar_foto(self):
        """Deleta a foto selecionada após confirmação do usuário."""
        if hasattr(self, 'foto_selecionada'):
            fotos_dir = "/home/lukas/Documents/Face-Scan-Id/fotos"
            foto_path = os.path.join(fotos_dir, self.foto_selecionada)  # type: ignore

            if os.path.exists(foto_path):
                confirmar = messagebox.askyesno("Confirmação", f"Tem certeza que deseja deletar a foto {self.foto_selecionada}?")
                print("Confirmação", f"Tem certeza que deseja deletar a foto {self.foto_selecionada}?")
                if confirmar:
                    print("Sim")
                    if hasattr(self, 'janela_ampliada') and self.janela_ampliada.winfo_exists():
                        self.janela_ampliada.destroy()

                    try:
                        os.remove(foto_path)

                        self.scrollable_frame.destroy()
                        self.scrollable_frame = ttk.Frame(self.canvas)
                        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

                        # Agora pode chamar carregar_thumbnails()
                        self.carregar_thumbnails()

                        #messagebox.showinfo("Sucesso", f"Foto {self.foto_selecionada} deletada com sucesso!")
                        print("Sucesso", f"Foto {self.foto_selecionada} deletada com sucesso!")
                        self.botao_deletar.config(state="disabled")  # Desativa o botão de deletar
                        self.foto_selecionada = None  # Limpa a seleção
                        
                    except Exception as e:
                        messagebox.showerror("Erro", f"Erro ao deletar a foto: {e}")
                        print("Erro", f"Erro ao deletar a foto: {e}")
                else:
                    print("Não")
            else:
                messagebox.showerror("Erro", "Foto não encontrada.")
                print("Erro", "Foto não encontrada.")
        else:
            messagebox.showerror("Erro", "Nenhuma foto selecionada para deletar.")
            print("Erro", "Nenhuma foto selecionada para deletar.")
        # Recarregar as fotos após exclusão
        self.carregar_thumbnails()

    def deletar_usuario(self):
        """Deleta todas as fotos e dados do usuário selecionado."""
        if hasattr(self, 'foto_selecionada'):
            fotos_dir = "/home/lukas/Documents/Face-Scan-Id/fotos"
            info_path = os.path.join(fotos_dir, "info.txt")

            foto = self.foto_selecionada
            if "_" not in foto: #type: ignore
                messagebox.showerror("Erro", "Nome da foto inválido. Esperado: id_nome.jpg")
                return

            id_usuario = foto.split("_")[0] #type: ignore

            confirmar = messagebox.askyesno("Confirmação", f"Tem certeza que deseja deletar o usuário ID {id_usuario} por completo?")
            if not confirmar:
                return
            if hasattr(self, 'janela_ampliada') and self.janela_ampliada.winfo_exists():
                self.janela_ampliada.destroy()

            try:
                # 1. Apagar todas as fotos com o ID
                fotos_apagadas = 0
                for arquivo in os.listdir(fotos_dir):
                    if arquivo.startswith(f"{id_usuario}_"):
                        os.remove(os.path.join(fotos_dir, arquivo))
                        fotos_apagadas += 1

               # 2. Remover entrada do info.txt
                if os.path.exists(info_path):
                    with open(info_path, "r") as f:
                        linhas = f.readlines()

                    with open(info_path, "w") as f:
                        for linha in linhas:
                            linha = linha.strip()
                            if linha == "":
                                continue  # Ignora linhas vazias
                            partes = linha.split(",")
                            if partes[0] != id_usuario:
                                f.write(linha + "\n")  # Garante quebra de linha ao reescrever


                # 3. Atualizar interface
                self.scrollable_frame.destroy()
                self.scrollable_frame = ttk.Frame(self.canvas)
                self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
                self.carregar_thumbnails()

                #messagebox.showinfo("Sucesso", f"Usuário ID {id_usuario} e {fotos_apagadas} foto(s) deletados com sucesso.")
                self.botao_deletar.config(state="disabled")
                self.foto_selecionada = None

            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao deletar usuário: {e}")
        else:
            messagebox.showerror("Erro", "Nenhuma foto selecionada para deletar o usuário.")


if __name__ == "__main__":
    root = tk.Tk()
    app = FaceRecognitionApp(root)
    root.mainloop()
