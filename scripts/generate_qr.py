"""Generate High-Resolution, Ultra-Crisp QR Code Poster for Hostel 1.

Generates professional, printable QR code images pointing directly to the web feedback form.

Usage:
    venv/Scripts/python.exe scripts/generate_qr.py
    venv/Scripts/python.exe scripts/generate_qr.py --url https://your-app-domain.com
"""

from __future__ import annotations

import argparse
from pathlib import Path
import qrcode
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "feedback_form"


def load_font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Safely load TrueType font with size, falling back gracefully."""
    font_candidates = [
        name,
        f"C:/Windows/Fonts/{name}",
        "arialbd.ttf",
        "arial.ttf",
        "DejaVuSans-Bold.ttf",
        "DejaVuSans.ttf",
    ]
    for font_name in font_candidates:
        try:
            return ImageFont.truetype(font_name, size)
        except Exception:
            continue
    return ImageFont.load_default()


import socket


def get_local_wifi_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def generate_qr(target_base_url: str = None) -> Path:
    if not target_base_url or "127.0.0.1" in target_base_url:
        local_ip = get_local_wifi_ip()
        target_base_url = f"http://{local_ip}:8000"

    target_base_url = target_base_url.rstrip("/")
    feedback_url = f"{target_base_url}/feedback_form/index.html?site_id=1"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # High error correction for crisp scanning
        box_size=16,
        border=3,
    )
    qr.add_data(feedback_url)
    qr.make(fit=True)

    # 1. Raw QR Image (High resolution 600x600)
    qr_img = qr.make_image(fill_color="#0f172a", back_color="#ffffff").convert("RGB")
    qr_img = qr_img.resize((500, 500), Image.Resampling.LANCZOS)

    # 2. Printable Poster Card (800 x 1050 px)
    card_w, card_h = 800, 1050
    card = Image.new("RGB", (card_w, card_h), "#0f172a")
    draw = ImageDraw.Draw(card)

    # Outer border accent frame
    draw.rectangle([15, 15, card_w - 15, card_h - 15], outline="#334155", width=4)
    draw.rectangle([25, 25, card_w - 25, card_h - 25], outline="#10b981", width=2)

    # Header Card Background
    draw.rectangle([35, 35, card_w - 35, 175], fill="#1e293b")

    # Fonts
    title_font = load_font("arialbd.ttf", 40)
    subtitle_font = load_font("arialbd.ttf", 28)
    sub_font = load_font("arial.ttf", 22)
    footer_font_bold = load_font("arialbd.ttf", 24)
    footer_font = load_font("arial.ttf", 20)

    # Header Text
    draw.text((60, 50), "🍱 FoodFlow AI", fill="#10b981", font=title_font)
    draw.text((60, 105), "HOSTEL 1 — DINER FEEDBACK", fill="#ffffff", font=subtitle_font)
    draw.text((60, 142), "Scan to tell us why food was left on your plate!", fill="#94a3b8", font=sub_font)

    # White Background Card for QR Code
    qr_bg_box = [(card_w - 540) // 2, 210, (card_w + 540) // 2, 750]
    draw.rectangle(qr_bg_box, fill="#ffffff", outline="#10b981", width=6)

    # Paste QR code centered inside white card
    qr_x = (card_w - 500) // 2
    qr_y = 230
    card.paste(qr_img, (qr_x, qr_y))

    # Footer Action Card Background
    draw.rectangle([35, 785, card_w - 35, 1015], fill="#1e293b", outline="#334155", width=2)

    # Footer Text (Centered & Large)
    f1 = "📱 SCAN WITH ANY PHONE CAMERA"
    f2 = "Takes only 15 seconds • No app download needed"
    f3 = "Directly influences tomorrow's cooking quantity & recipes"

    draw.text((card_w // 2, 825), f1, fill="#f8fafc", font=footer_font_bold, anchor="mm")
    draw.text((card_w // 2, 870), f2, fill="#cbd5e1", font=footer_font, anchor="mm")
    draw.text((card_w // 2, 930), f3, fill="#10b981", font=footer_font_bold, anchor="mm")
    draw.text((card_w // 2, 975), "Hostel 1 Mess • Plate Return Counter", fill="#64748b", font=footer_font, anchor="mm")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "hostel1_qr_code.png"
    card.save(output_path, quality=95)

    # Save raw QR code image
    raw_path = OUTPUT_DIR / "hostel1_qr_raw.png"
    qr_img.save(raw_path, quality=95)

    print()
    print("==========================================")
    print("HIGH-RES CRISP QR POSTER GENERATED")
    print("==========================================")
    print(f"Target URL: {feedback_url}")
    print(f"Poster Card: {output_path} (800x1050 px)")
    print(f"Raw QR Code: {raw_path} (500x500 px)")
    print()

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Hostel 1 Diner Feedback QR Code.")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Base URL of deployed app")
    args = parser.parse_args()
    generate_qr(args.url)


if __name__ == "__main__":
    main()
