import requests

# URL do roteador
url = "http://10.0.1.1/goform/wirelessBasic"

# Cabeçalhos necessários
headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "http://10.0.1.1",
    "Referer": "http://10.0.1.1/wireless_basic.asp",
    "Cookie": "admin:language=pt"
}

# Corpo fixo do POST (exceto o broadcastssid)
post_base = {
    "enablewireless": "1",
    "enablewirelessEx": "1",
    "WirelessT": "0",
    "wirelessmode": "9",
    "bssid_num": "1",
    "ssid": "BLOQUEADO_5G",
    "mssid_1": "",
    "ap_isolate": "0",
    "sz11gChannel": "6",
    "n_bandwidth": "1",
    "n_extcha": "0",
    "wmm_capable": "on",
    "apsd_capable": "off",
    "wds_1": "",
    "ssid_1": "",
    "schannel_1": "",
    "wds_2": "",
    "ssid_2": "",
    "schannel_2": "",
    "wds_list": "1"
}

def alterar_divulgacao_ssid(ativar=True):
    dados = post_base.copy()
    dados["broadcastssid"] = "0" if ativar else "1"

    try:
        resposta = requests.post(url, headers=headers, data=dados, timeout=5)
        if resposta.status_code in [200, 302]:
            print("✅ Comando enviado com sucesso!")
            print("🔊 Divulgação do SSID ativada." if ativar else "🔒 Divulgação do SSID desativada.")
        else:
            print(f"⚠️ Erro ao enviar comando. Código: {resposta.status_code}")
    except Exception as e:
        print("❌ Erro de conexão:", e)

# Menu simples
print("=== Controle de Divulgação do SSID ===")
print("1 - Ativar (mostrar nome da rede Wi-Fi)")
print("2 - Desativar (ocultar nome da rede Wi-Fi)")
opcao = input("Escolha uma opção (1 ou 2): ")

if opcao == "1":
    alterar_divulgacao_ssid(ativar=True)
elif opcao == "2":
    alterar_divulgacao_ssid(ativar=False)
else:
    print("❌ Opção inválida.")
