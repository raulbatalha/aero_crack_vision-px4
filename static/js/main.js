let cameraStream = null;
let currentImageName = "drone.png";

const droneImage = document.getElementById("droneImage");
const resultLog = document.getElementById("result-log");
const downloadBtn = document.getElementById("download-btn");
const status = document.getElementById("status");
const reportPreview = document.getElementById("report-preview");
const alertaVisual = document.getElementById("alerta-visual");
const cameraFeed = document.getElementById("camera-feed");

function pararCameraAoVivo() {
  if (cameraStream) {
    cameraStream.getTracks().forEach(track => track.stop());
    cameraStream = null;
  }

  const img = document.createElement("img");
  img.id = "droneImage";
  img.src = droneImage.src || "static/images/drone.png";
  img.alt = "Camera do Drone";
  img.style.width = "100%";
  img.style.height = "100%";
  img.style.objectFit = "cover";

  cameraFeed.innerHTML = "";
  cameraFeed.appendChild(img);
}

function ativarCameraAoVivo() {
  pararCameraAoVivo();

  navigator.mediaDevices.getUserMedia({ video: true })
    .then(stream => {
      cameraStream = stream;
      const video = document.createElement("video");
      video.srcObject = stream;
      video.autoplay = true;
      video.playsInline = true;
      video.style.width = "100%";
      video.style.height = "100%";
      cameraFeed.innerHTML = "";
      cameraFeed.appendChild(video);
    })
    .catch(() => alert("Câmera não disponível!"));
}

async function uploadImage() {
  pararCameraAoVivo();

  const fileInput = document.getElementById("file");
  const file = fileInput.files[0];
  const formData = new FormData();
  formData.append("file", file);
  await fetch("/upload", { method: "POST", body: formData });
  currentImageName = file.name;

  const img = document.createElement("img");
  img.id = "droneImage";
  img.src = `static/uploads/${file.name}`;
  img.alt = "Camera do Drone";
  img.style.width = "100%";
  img.style.height = "100%";
  img.style.objectFit = "cover";

  cameraFeed.innerHTML = "";
  cameraFeed.appendChild(img);

  status.textContent = "📷 Imagem carregada";
}

async function captureFrame() {
  const video = document.querySelector("video");
  if (!video) return alert("Câmera não ativa");

  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d").drawImage(video, 0, 0);

  canvas.toBlob(async (blob) => {
    const formData = new FormData();
    const filename = `captura_${Date.now()}.jpg`;
    formData.append("file", blob, filename);
    await fetch("/upload", { method: "POST", body: formData });
    currentImageName = filename;

    pararCameraAoVivo();

    const img = document.createElement("img");
    img.id = "droneImage";
    img.src = URL.createObjectURL(blob);
    img.alt = "Camera do Drone";
    img.style.width = "100%";
    img.style.height = "100%";
    img.style.objectFit = "cover";

    cameraFeed.innerHTML = "";
    cameraFeed.appendChild(img);

    status.textContent = "📸 Frame capturado";
  });
}

async function analyzeCurrent() {
  if (!currentImageName) return alert("Nenhuma imagem disponível");
  status.textContent = "⏳ Analisando...";

  const res = await fetch("/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image: currentImageName })
  });
  const data = await res.json();

  resultLog.textContent = data.fissura
    ? `Fissura detectada (${(data.conf * 100).toFixed(1)}%)\nLargura estimada: ${data.largura} mm`
    : `Nenhuma fissura detectada (${(data.conf * 100).toFixed(1)}%)`;

  status.textContent = "📊 Análise concluída";

  if (data.imagem_resultado) {
    const img = document.createElement("img");
    img.id = "droneImage";
    img.src = data.imagem_resultado;
    img.alt = "Resultado da Análise";
    img.style.width = "100%";
    img.style.height = "100%";
    img.style.objectFit = "cover";
    cameraFeed.innerHTML = "";
    cameraFeed.appendChild(img);
  }

  if (data.relatorio_preview) {
    reportPreview.src = data.relatorio_preview;
    reportPreview.style.display = "block";
  }
  downloadBtn.style.display = "block";
  downloadBtn.onclick = () => window.open(data.relatorio, "_blank");

  alertaVisual.style.display = data.fissura ? "block" : "none";
  cameraFeed.classList.remove("video-ok", "video-alerta");
  cameraFeed.classList.add(data.fissura ? "video-alerta" : "video-ok");
}

function atualizarGPS() {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(pos => {
      document.getElementById("gps").textContent = `📍 ${pos.coords.latitude.toFixed(6)}, ${pos.coords.longitude.toFixed(6)}`;
      document.getElementById("altitude").textContent = `🛫 ${pos.coords.altitude || 'Indefinida'} m`;
    });
  }
}

function ativarDeteccaoTempoReal() {
  const img = document.createElement("img");
  img.src = "/video_feed";
  img.alt = "Detecção em Tempo Real";
  img.style.width = "100%";
  img.style.height = "100%";
  img.style.objectFit = "cover";
  img.style.border = "3px solid cyan";
  img.id = "streaming-deteccao";

  cameraFeed.innerHTML = "";
  cameraFeed.appendChild(img);

  status.textContent = "Detecção em tempo real ativa";
  resultLog.textContent = "Aguardando detecção ao vivo...";
}

async function pararDeteccaoTempoReal() {
  const res = await fetch("/stop_video", { method: "POST" });
  const data = await res.json();

  const container = document.getElementById("camera-feed");
  container.innerHTML = "";

  if (data.frame_salvo) {
    const img = document.createElement("img");
    img.src = `static/detected/${data.frame_salvo}`;
    img.alt = "Última Detecção";
    img.style.width = "100%";
    img.style.height = "100%";
    img.style.objectFit = "cover";
    img.style.border = "2px solid red";
    container.appendChild(img);

    status.textContent = "📸 Última fissura capturada";
    resultLog.textContent = "Relatório gerado automaticamente.";

    // PREVIEW DO RELATÓRIO
    if (data.preview) {
      reportPreview.src = data.preview;
      reportPreview.style.display = "block";
    }

    // BOTÃO DE DOWNLOAD
    if (data.relatorio) {
      downloadBtn.style.display = "block";
      downloadBtn.onclick = () => window.open(data.relatorio, "_blank");
    }

    alertaVisual.style.display = "block";
    cameraFeed.classList.remove("video-ok", "video-alerta");
    cameraFeed.classList.add("video-alerta");
  } else {
    const standbyImg = document.createElement("img");
    standbyImg.src = "static/images/drone.png";
    standbyImg.alt = "Câmera offline";
    standbyImg.style.width = "100%";
    standbyImg.style.height = "100%";
    standbyImg.style.objectFit = "cover";
    standbyImg.style.border = "2px dashed gray";
    container.appendChild(standbyImg);

    status.textContent = "Detecção parada (nenhuma fissura detectada)";
    resultLog.textContent = "Em modo de espera.";
    alertaVisual.style.display = "none";
    downloadBtn.style.display = "none";
    reportPreview.style.display = "none";
    cameraFeed.classList.remove("video-ok", "video-alerta");
  }
}


setInterval(atualizarGPS, 3000);