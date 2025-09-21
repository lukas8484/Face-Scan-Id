import cv2
import time

# Inicia a câmera
camera = cv2.VideoCapture(0)

# Define a resolução (opcional, melhora o desempenho)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Carrega os classificadores Haar
face_cascade = cv2.CascadeClassifier('VARIADOS CASCADES/haarcascade_frontalface_default.xml')
smile_cascade = cv2.CascadeClassifier('VARIADOS CASCADES/haarcascade_smile.xml')

# Inicializa tempo para cálculo de FPS
prev_time = time.time()

while True:
    check, img = camera.read()
    if not check:
        break

    imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Detectar rostos
    faces = face_cascade.detectMultiScale(imgGray, scaleFactor=1.3, minNeighbors=5)

    for (x, y, w, h) in faces:
        # Desenhar retângulo ao redor do rosto
        cv2.rectangle(img, (x, y), (x+w, y+h), (255, 0, 0), 2)

        # Recorte da região do rosto
        roi_gray = imgGray[y:y+h, x:x+w]
        roi_color = img[y:y+h, x:x+w]

        # Detectar sorriso dentro do rosto
        smiles = smile_cascade.detectMultiScale(
            roi_gray,
            scaleFactor=1.7,
            minNeighbors=20,
            minSize=(25, 25)
        )

        for (sx, sy, sw, sh) in smiles:
            # Desenhar retângulo ao redor do sorriso
            cv2.rectangle(roi_color, (sx, sy), (sx+sw, sy+sh), (0, 255, 0), 2)

        # Se houver sorriso, mostrar texto
        if len(smiles) > 0:
            cv2.putText(img, 'Sorriso detectado!', (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

    # Cálculo e exibição de FPS
    curr_time = time.time()
    fps = 1 / (curr_time - prev_time)
    prev_time = curr_time
    cv2.putText(img, f'FPS: {int(fps)}', (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    # Exibir imagem
    cv2.imshow('smile', img)

    # Pressione ESC para sair
    if cv2.waitKey(1) & 0xFF == 27:
        break

# Finaliza
camera.release()
cv2.destroyAllWindows()
