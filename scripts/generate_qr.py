"""Generate High-Resolution, Ultra-Crisp QR Code Poster for Hostel 1.

Generates professional, printable QR code images pointing directly to the web feedback form.
Restyled with the FoodFlow AI white and navy enterprise design system.

Usage:
    venv/Scripts/python.exe scripts/generate_qr.py
    venv/Scripts/python.exe scripts/generate_qr.py --url https://your-app-domain.com
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import socket
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


def get_local_wifi_ip() -> str:
    """Detect active local network IPv4 address (e.g. 192.168.x.x, 10.x.x.x)."""
    # Strategy 1: Probe external DNS to find outbound routing interface
    for probe_host in [("8.8.8.8", 80), ("1.1.1.1", 80), ("208.67.222.222", 80)]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.6)
            s.connect(probe_host)
            ip = s.getsockname()[0]
            s.close()
            if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
                return ip
        except Exception:
            pass

    # Strategy 2: Inspect all interfaces on hostname
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if (
                ip.startswith("192.168.")
                or ip.startswith("10.")
                or (ip.startswith("172.") and 16 <= int(ip.split(".")[1]) <= 31)
            ):
                return ip
    except Exception:
        pass

    return "127.0.0.1"


def resolve_target_base_url(target_base_url: str | None = None) -> tuple[str, str]:
    """Resolve target base URL and return (base_url, environment_source)."""
    # 1. Explicit CLI or argument override (if valid and not localhost/127.0.0.1)
    if target_base_url and "127.0.0.1" not in target_base_url and "localhost" not in target_base_url:
        return target_base_url.rstrip("/"), "CLI / Argument"

    # 2. Render cloud deployment detection
    is_render = os.environ.get("RENDER") == "true" or "RENDER_EXTERNAL_HOSTNAME" in os.environ
    render_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
    render_url = os.environ.get("RENDER_EXTERNAL_URL")

    if is_render and render_hostname:
        clean_host = render_hostname.strip().rstrip("/")
        if not clean_host.startswith("http://") and not clean_host.startswith("https://"):
            return f"https://{clean_host}", "Render ($RENDER_EXTERNAL_HOSTNAME)"
        return clean_host, "Render ($RENDER_EXTERNAL_HOSTNAME)"

    if is_render and render_url:
        return render_url.strip().rstrip("/"), "Render ($RENDER_EXTERNAL_URL)"

    # 3. Explicit DEPLOY_URL or PUBLIC_URL environment variable
    custom_deploy_url = os.environ.get("DEPLOY_URL") or os.environ.get("PUBLIC_URL")
    if custom_deploy_url:
        return custom_deploy_url.strip().rstrip("/"), "Environment ($DEPLOY_URL)"

    # 4. Streamlit Community Cloud
    if os.path.exists("/mount/src/foodflow_ai") or os.environ.get("STREAMLIT_SHARING_HOST"):
        return "https://foodflowai-vatb3mag7rsfwenohcxu5b.streamlit.app", "Streamlit Community Cloud"

    # 5. Local fallback: detected Wi-Fi IP on Streamlit port
    detected_ip = get_local_wifi_ip()
    port = os.environ.get("PORT", "8501")
    return f"http://{detected_ip}:{port}", f"Local Wi-Fi ({detected_ip}:{port})"


def generate_qr(target_base_url: str | None = None) -> Path:
    """Generate both printable poster card and raw QR code image with verified URL."""
    target_base_url, env_source = resolve_target_base_url(target_base_url)
    feedback_url = f"{target_base_url}/?mode=feedback&site_id=1"

    # Crisp QR code with High Error Correction
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=16,
        border=2,
    )
    qr.add_data(feedback_url)
    qr.make(fit=True)

    # 1. Raw QR Code with FoodFlow Navy module color
    qr_img = qr.make_image(fill_color="#1E3A5F", back_color="#FFFFFF").convert("RGB")
    qr_img = qr_img.resize((500, 500), Image.Resampling.LANCZOS)

    # 2. Printable Poster Card (800 x 1050 px) matching SaaS design
    card_w, card_h = 800, 1050
    card = Image.new("RGB", (card_w, card_h), "#F8F9FA")
    draw = ImageDraw.Draw(card)

    # Outer border and subtle frame
    draw.rectangle([15, 15, card_w - 15, card_h - 15], fill="#F8F9FA", outline="#E5E7EB", width=3)
    draw.rectangle([25, 25, card_w - 25, card_h - 25], outline="#1E3A5F", width=2)

    # Header Card Background (Clean White)
    draw.rectangle([40, 40, card_w - 40, 185], fill="#FFFFFF", outline="#E5E7EB", width=2)

    # Brand Logo Icon (Navy Square with white F)
    draw.rectangle([65, 62, 115, 112], fill="#1E3A5F")
    logo_font = load_font("arialbd.ttf", 34)
    draw.text((90, 87), "F", fill="#FFFFFF", font=logo_font, anchor="mm")

    # Fonts
    title_font = load_font("arialbd.ttf", 36)
    subtitle_font = load_font("arialbd.ttf", 26)
    sub_font = load_font("arial.ttf", 20)
    footer_title = load_font("arialbd.ttf", 24)
    footer_text = load_font("arial.ttf", 19)
    footer_teal = load_font("arialbd.ttf", 20)
    url_font = load_font("arialbd.ttf", 18)

    # Header Text
    draw.text((130, 60), "FoodFlow AI", fill="#1E3A5F", font=title_font)
    draw.text((130, 104), "HOSTEL 1 — DINER FEEDBACK", fill="#1E293B", font=subtitle_font)
    draw.text((65, 145), "Scan with your phone to tell us why food was left on your plate", fill="#64748B", font=sub_font)

    # Center Card for QR Code (White with crisp border)
    qr_bg_box = [(card_w - 540) // 2, 215, (card_w + 540) // 2, 755]
    draw.rectangle(qr_bg_box, fill="#FFFFFF", outline="#E5E7EB", width=2)
    # Subtle inner accent border around QR
    draw.rectangle([(card_w - 520) // 2, 225, (card_w + 520) // 2, 745], outline="#1E3A5F", width=1)

    # Paste QR centered inside card
    qr_x = (card_w - 500) // 2
    qr_y = 235
    card.paste(qr_img, (qr_x, qr_y))

    # Direct URL banner below QR
    draw.rectangle([(card_w - 540) // 2, 765, (card_w + 540) // 2, 805], fill="#FFFFFF", outline="#E5E7EB", width=1)
    draw.text((card_w // 2, 785), f"URL: {feedback_url}", fill="#1E3A5F", font=url_font, anchor="mm")

    # Footer Card Background (White)
    draw.rectangle([40, 825, card_w - 40, 1015], fill="#FFFFFF", outline="#E5E7EB", width=2)

    # Footer Text
    f1 = "SCAN WITH ANY PHONE CAMERA"
    f2 = "Takes only 15 seconds • No app download required"
    f3 = "Directly influences tomorrow's cooking quantities & recipes"
    f4 = "Hostel 1 Mess • Plate Return Counter"

    draw.text((card_w // 2, 860), f1, fill="#1E3A5F", font=footer_title, anchor="mm")
    draw.text((card_w // 2, 905), f2, fill="#475569", font=footer_text, anchor="mm")
    draw.text((card_w // 2, 945), f3, fill="#0F766E", font=footer_teal, anchor="mm")
    draw.text((card_w // 2, 982), f4, fill="#94A3B8", font=footer_text, anchor="mm")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "hostel1_qr_code.png"
    card.save(output_path, quality=95)

    raw_path = OUTPUT_DIR / "hostel1_qr_raw.png"
    qr_img.save(raw_path, quality=95)

    print()
    print("================================================================")
    print(" FOODFLOW AI — CRISP QR POSTER REGENERATED")
    print("================================================================")
    print(f" Environment Source:  {env_source}")
    print(f" Target Server URL:   {target_base_url}")
    print(f" Exact QR Payload:    {feedback_url}")
    print(f" Printable Poster:    {output_path} (800x1050 px)")
    print(f" Raw QR Code Image:   {raw_path} (500x500 px)")
    print(" Reachability Check:  curl -I " + f"{target_base_url}/health")
    print("================================================================")
    print()

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Hostel 1 Diner Feedback QR Code.")
    parser.add_argument("--url", default=None, help="Base URL of deployed app (e.g. http://192.168.0.15:8000)")
    args = parser.parse_args()
    generate_qr(args.url)


if __name__ == "__main__":
    main()
