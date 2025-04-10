from fpdf import FPDF
from datetime import datetime
import os
from PIL import Image

def generate_report(image_path, boxed_path, is_cracked, confidence, fissura_largura, gps, output_path="report.pdf", preview_path=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)

    # Cabeçalho
    pdf.set_fill_color(200, 220, 255)
    pdf.set_text_color(0)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, "RELATÓRIO DE INSPEÇÃO DE FISSURAS ESTRUTURAIS", 1, 1, 'C', True)
    pdf.ln(5)

    pdf.set_font("Arial", '', 11)
    pdf.cell(95, 10, f"Data do Relatório: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0)
    pdf.cell(95, 10, f"Projeto Nº: 001-A", 0, 1)
    pdf.cell(95, 10, f"Responsável: Sistema de Drone Autônomo", 0)
    pdf.cell(95, 10, f"Região GPS: {gps['lat']} S, {gps['lon']} W", 0, 1)
    pdf.ln(5)

    # Visão Geral da Inspeção
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 8, "VISÃO GERAL DA INSPEÇÃO", 1, 1, 'C')
    pdf.set_font("Arial", '', 11)
    pdf.cell(47, 8, "Imagem Analisada", 1)
    pdf.cell(47, 8, "Fissura Detectada", 1)
    pdf.cell(47, 8, "Confiança IA", 1)
    pdf.cell(49, 8, "Largura Estimada", 1, 1)

    pdf.cell(47, 8, os.path.basename(image_path), 1)
    pdf.cell(47, 8, "SIM" if is_cracked else "NÃO", 1)
    pdf.cell(47, 8, f"{confidence*100:.2f}%", 1)
    pdf.cell(49, 8, f"{fissura_largura:.2f} mm", 1, 1)
    pdf.ln(5)

    # Imagem com bounding box
    if os.path.exists(boxed_path):
        try:
            pdf.image(boxed_path, x=30, w=150)
        except RuntimeError:
            pdf.cell(190, 10, "[Falha ao carregar imagem com bounding box]", 0, 1, 'C')
    pdf.ln(10)

    # Gera preview se solicitado
    if preview_path:
        try:
            img = Image.open(boxed_path)
            img.save(preview_path)
        except Exception as e:
            print(f"Erro ao salvar preview: {e}")

    # Análise técnica detalhada
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 8, "ANÁLISE TÉCNICA E CRÍTICA", 1, 1, 'C')
    pdf.set_font("Arial", '', 11)

    if is_cracked:
        analise = (
            f"A presença de fissura foi confirmada por Inteligengia Artificial com alta confiança. A largura estimada de "
            f"{fissura_largura:.2f} mm pode indicar risco estrutural significativo dependendo do material e profundidade.\n\n"
            "Recomenda-se:\n"
            "- Inspeção técnica presencial;\n"
            "- Aplicação de ensaios não destrutivos (END);\n"
            "- Análise do histórico da estrutura;\n"
            "- Reforço ou reparo preventivo se necessário."
        )
    else:
        analise = (
            "Não foram detectadas fissuras relevantes na imagem analisada. A estrutura aparenta integridade visual. "
            "É recomendado manter inspeções regulares para prevenir falhas ocultas."
        )

    pdf.multi_cell(0, 8, analise)

    # Rodapé
    pdf.set_y(-30)
    pdf.set_font("Arial", 'I', 9)
    pdf.cell(0, 10, 'Relatório gerado automaticamente pelo sistema de inspeção com drone - IFAM 2025', 0, 0, 'C')

    pdf.output(output_path)
    return output_path
    return output_path