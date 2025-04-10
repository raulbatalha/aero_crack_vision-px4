from flask import Flask, request, jsonify, send_file, render_template, redirect, url_for, Response
from flask_cors import CORS
from PIL import Image
import cv2
import torch
import os
import csv
import io
import datetime
import random
import matplotlib.pyplot as plt
from ultralytics import YOLO
from report_generator import generate_report

app = Flask(__name__, template_folder="templates")
CORS(app)


# --------------------------- CONFIGURAÇÕES ---------------------------
MODEL_PATH = "app/crackDetect50epoch.pt"
IMAGE_DIR = "static/images"
UPLOAD_DIR = "static/uploads"
DETECTED_DIR = "static/detected"
REPORT_DIR = "reports"
REPORT_PREVIEW_DIR = "static/reports"
HISTORY_FILE = "analysis_log.csv"

os.makedirs(REPORT_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DETECTED_DIR, exist_ok=True)
os.makedirs(REPORT_PREVIEW_DIR, exist_ok=True)

streaming = False
last_detected_frame = None
last_detection_time = None
last_conf = 0.0
last_largura = 0.0
last_gps = {}


model = YOLO(MODEL_PATH)

# --------------------------- STREAM AO VIVO COM DETECÇÃO ---------------------------
def gen_frames():
    global streaming, last_detected_frame, last_detection_time, last_conf, last_largura, last_gps

    cap = cv2.VideoCapture(0)
    streaming = True

    if not cap.isOpened():
        raise RuntimeError("Não foi possível acessar a câmera.")

    while streaming:
        success, frame = cap.read()
        if not success:
            break

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        from PIL import Image
        pil_image = Image.fromarray(rgb_frame)
        results = model(pil_image)
        annotated = results[0].plot()
        boxes = results[0].boxes

        if boxes and len(boxes) > 0:
            print("✅ Fissura detectada no vídeo ao vivo!")
            last_detected_frame = annotated.copy()
            last_detection_time = datetime.datetime.now().strftime("%Y%m%d")

            bbox = boxes.xyxy[0]
            largura_px = bbox[2] - bbox[0]
            last_largura = round(float(largura_px) * 0.25, 2)
            last_conf = float(torch.max(boxes.conf))

            last_gps = {
                "lat": round(random.uniform(-3.13, -3.12), 6),
                "lon": round(random.uniform(-60.02, -60.01), 6)
            }

        _, buffer = cv2.imencode('.jpg', annotated)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    cap.release()


# --------------------------- ROTA DO VIDEO ---------------------------
@app.route("/video_feed")
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/stop_video", methods=["POST"])
def stop_video():
    global streaming, last_detected_frame, last_detection_time
    global last_conf, last_largura, last_gps

    streaming = False

    if last_detected_frame is not None and last_detection_time:
        # Nome do frame salvo
        filename = f"ao_vivo_{last_detection_time}.jpg"
        frame_path = os.path.join(DETECTED_DIR, filename)
        Image.fromarray(last_detected_frame).save(frame_path)
        print(f"💾 Frame salvo em {frame_path}")

        # Corrigir extensão: remove .jpg antes de montar nome do relatório
        base_name = os.path.splitext(filename)[0]

        # Gerar nomes corretos do relatório e preview
        report_name = f"relatorio_{base_name}.pdf"
        report_path = os.path.join(REPORT_DIR, report_name)

        preview_name = f"preview_{base_name}.png"
        preview_path = os.path.join(REPORT_PREVIEW_DIR, preview_name)

        try:
            generate_report(
                image_path=frame_path,
                boxed_path=frame_path,
                is_cracked=True,
                confidence=last_conf,
                fissura_largura=last_largura,
                gps=last_gps,
                output_path=report_path,
                preview_path=preview_path
            )
            print(f"📄 Relatório salvo em {report_path}")
        except Exception as e:
            print(f"⚠️ Erro ao gerar relatório: {e}")

        return jsonify({
            "status": "stream encerrado",
            "frame_salvo": filename,
            "relatorio": f"/download/{report_name}",
            "preview": f"/{preview_path}"
        })

    return jsonify({
        "status": "stream encerrado",
        "frame_salvo": None
    })

# --------------------------- ROTA PRINCIPAL ---------------------------
@app.route("/")
def home():
    return render_template("index.html")

# --------------------------- ANÁLISE MANUAL ---------------------------
@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    image_name = data.get("image")

    image_path = os.path.join(IMAGE_DIR, image_name)
    if not os.path.exists(image_path):
        image_path = os.path.join(UPLOAD_DIR, image_name)
    if not os.path.exists(image_path):
        return jsonify({"error": "Image not found"}), 404

    results = model(image_path)
    boxes = results[0].boxes
    is_cracked = len(boxes) > 0
    conf = float(torch.max(boxes.conf)) if is_cracked else 0.0
    label = "com_fissura" if is_cracked else "sem_fissura"

    fissura_largura_mm = 0.0
    if is_cracked:
        bbox = boxes.xyxy[0]
        largura_px = bbox[2] - bbox[0]
        fissura_largura_mm = round(float(largura_px) * 0.25, 2)

    boxed = results[0].plot()
    boxed_path = os.path.join(DETECTED_DIR, f"boxed_{image_name}")
    Image.fromarray(boxed).save(boxed_path)

    gps_coords = {
        "lat": round(random.uniform(-3.13, -3.12), 6),
        "lon": round(random.uniform(-60.02, -60.01), 6)
    }

    report_pdf = os.path.join(REPORT_DIR, f"relatorio_{image_name}.pdf")
    report_preview = os.path.join(REPORT_PREVIEW_DIR, f"preview_{image_name}.png")

    generate_report(
        image_path=image_path,
        boxed_path=boxed_path,
        is_cracked=is_cracked,
        confidence=conf,
        fissura_largura=fissura_largura_mm,
        gps=gps_coords,
        output_path=report_pdf,
        preview_path=report_preview
    )

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(HISTORY_FILE, mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([image_name, label, conf, fissura_largura_mm, gps_coords['lat'], gps_coords['lon'], timestamp])

    return jsonify({
        "fissura": is_cracked,
        "conf": conf,
        "largura": fissura_largura_mm,
        "gps": gps_coords,
        "relatorio": f"/download/{os.path.basename(report_pdf)}",
        "relatorio_preview": f"/{report_preview}",
        "imagem_resultado": f"/{boxed_path}"
    })

# --------------------------- UPLOAD DE IMAGEM ---------------------------
@app.route("/upload", methods=["POST"])
def upload():
    file = request.files['file']
    if file and file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        path = os.path.join(UPLOAD_DIR, file.filename)
        file.save(path)
        return redirect(url_for('home'))
    return "Formato inválido", 400

# --------------------------- DOWNLOAD DE RELATÓRIO PDF ---------------------------
@app.route("/download/<filename>")
def download(filename):
    file_path = os.path.join(app.root_path, REPORT_DIR, filename)
    if os.path.exists(file_path):
        print(f"⬇️ Baixando {filename}...")
        return send_file(file_path, as_attachment=True)
    return jsonify({"error": f"Arquivo {filename} não encontrado"}), 404


# --------------------------- DOWNLOAD CSV ---------------------------
@app.route("/csv")
def download_csv():
    if not os.path.exists(HISTORY_FILE):
        return "Nenhum dado disponível."
    return send_file(HISTORY_FILE, as_attachment=True)

# --------------------------- GRÁFICO DE HISTÓRICO ---------------------------
@app.route("/history")
def plot_history():
    if not os.path.exists(HISTORY_FILE):
        return "Sem histórico"

    labels = []
    with open(HISTORY_FILE) as f:
        reader = csv.reader(f)
        for row in reader:
            if row:
                labels.append(row[1])

    cracked = labels.count("com_fissura")
    no_crack = labels.count("sem_fissura")

    fig, ax = plt.subplots()
    ax.bar(["Com fissura", "Sem fissura"], [cracked, no_crack], color=['red', 'green'])
    ax.set_ylabel("Total")
    ax.set_title("Histórico de Análises")

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    return send_file(img, mimetype='image/png')

# --------------------------- INICIAR SERVIDOR ---------------------------
#if __name__ == "__main__":
#    app.run(debug=True)
