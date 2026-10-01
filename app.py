#!/usr/bin/env python3
"""
⚡ TikTok Zefoy Comments Hearts Booster - Render Web Service Edition ⚡
Tích hợp Web Server giám sát tiến độ + Chạy bot ngầm 24/7 với Gemini AI Captcha Solver.
"""

import os
import re
import sys
import time
import base64
import asyncio
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from playwright.async_api import async_playwright

ZEFOY_URL = "https://zefoy.com/"
DEFAULT_GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3.5-flash-lite"
TARGET_URL = os.getenv("TIKTOK_URL", "https://www.tiktok.com/@toandinh0207/photo/7681249165866814741")
KEYWORD = os.getenv("COMMENT_KEYWORD", "").lower().strip() or None
USERNAME = os.getenv("COMMENT_USERNAME", "").lower().strip() or None
COMMENT_INDEX = int(os.getenv("COMMENT_INDEX", "0"))
PORT = int(os.getenv("PORT", "10000"))

# Trạng thái toàn cục hiển thị lên Dashboard
STATUS = {
    "total_sent": 0,
    "current_status": "Khởi động...",
    "cooldown": "Đang kiểm tra...",
    "uptime_start": time.time(),
    "last_update": "",
    "logs": []
}

def log(msg):
    timestamp = time.strftime("%H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    print(entry, flush=True)
    STATUS["logs"].append(entry)
    if len(STATUS["logs"]) > 40:
        STATUS["logs"].pop(0)
    STATUS["last_update"] = timestamp

class SimpleWebServer(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        uptime = int(time.time() - STATUS["uptime_start"])
        logs_html = "<br>".join(reversed(STATUS["logs"]))
        filter_desc = f"Keyword: '{KEYWORD}'" if KEYWORD else (f"User: '{USERNAME}'" if USERNAME else "Bình luận đầu tiên")

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Zefoy Comments Hearts Booster Status</title>
    <meta http-equiv="refresh" content="5">
    <style>
        body {{ font-family: monospace; background: #0d1117; color: #58a6ff; padding: 20px; }}
        .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; max-width: 800px; margin: auto; }}
        h2 {{ color: #f778ba; }}
        .badge {{ background: #bf4b8a; color: white; padding: 4px 8px; border-radius: 4px; }}
        .log-box {{ background: #000; color: #7ee787; padding: 15px; border-radius: 5px; height: 350px; overflow-y: auto; font-size: 13px; }}
    </style>
</head>
<body>
    <div class="card">
        <h2>💖 Zefoy Comments Hearts Booster (24/7 Cloud)</h2>
        <p><b>Video:</b> <a href="{TARGET_URL}" target="_blank" style="color: #79c0ff;">{TARGET_URL}</a></p>
        <p><b>Mục tiêu buff:</b> <span style="color: #e3b341;">{filter_desc}</span></p>
        <p><b>Trạng thái:</b> <span class="badge">{STATUS['current_status']}</span></p>
        <p><b>Thời gian Cooldown còn lại:</b> <span style="font-size: 22px; font-weight: bold; color: #f0883e;">⏳ {STATUS['cooldown']}</span></p>
        <p><b>Tổng lượt buff tim thành công:</b> <span style="font-size: 22px; font-weight: bold; color: #f778ba;">{STATUS['total_sent']}</span></p>
        <p><b>Uptime:</b> {uptime}s | <b>Cập nhật lần cuối:</b> {STATUS['last_update']}</p>
        <h3>Nhật ký hoạt động (Tự refresh 5s):</h3>
        <div class="log-box">{logs_html}</div>
    </div>
</body>
</html>"""
        self.wfile.write(html.encode("utf-8"))

def start_web_server():
    server = HTTPServer(("0.0.0.0", PORT), SimpleWebServer)
    log(f"Web server giám sát đang chạy trên port {PORT}")
    server.serve_forever()

class ZefoyCommentsHeartsBot:
    def __init__(self, target_url, api_key):
        self.target_url = target_url
        self.api_key = api_key

    def solve_captcha_api(self, image_bytes):
        b64_img = base64.b64encode(image_bytes).decode('utf-8')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={self.api_key}"
        prompt = "This is a text captcha image. Read the word or letters shown in this image. Output ONLY the letters in lowercase, with no spaces."
        payload = {
            "contents": [{"parts": [{"text": prompt}, {"inlineData": {"mimeType": "image/png", "data": b64_img}}]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": 20}
        }
        try:
            res = requests.post(url, json=payload, timeout=12)
            if res.status_code == 200:
                raw_text = res.json()['candidates'][0]['content']['parts'][0]['text']
                return re.sub(r'[^a-zA-Z]', '', raw_text).lower().strip()
        except Exception as e:
            log(f"Lỗi gọi Gemini API: {e}")
        return None

    async def run(self):
        STATUS["current_status"] = "Đang mở trình duyệt..."
        log("Khởi động Playwright...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=['--no-sandbox', '--disable-blink-features=AutomationControlled', '--disable-infobars']
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => false });")

            STATUS["current_status"] = "Đang nạp Zefoy..."
            log("Truy cập zefoy.com...")
            await page.goto(ZEFOY_URL, wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(3)

            # Giải Captcha tự động qua Gemini AI
            content = await page.content()
            if 'captchalogin' in content:
                STATUS["current_status"] = "Đang giải Captcha bằng AI..."
                for attempt in range(1, 6):
                    log(f"AI giải Captcha lần #{attempt}...")
                    captcha_img = page.locator('#captcha-img')
                    await captcha_img.wait_for(state="visible", timeout=15000)
                    await asyncio.sleep(1)
                    img_bytes = await captcha_img.screenshot()
                    
                    text = self.solve_captcha_api(img_bytes)
                    if not text:
                        continue
                    log(f"Gemini nhận diện từ: '{text}'")
                    input_cap = page.locator('input[name="captchalogin"]')
                    await input_cap.fill(text)
                    await asyncio.sleep(0.5)
                    await page.locator('button.submit-captcha, button[type="submit"]').first.click()
                    await asyncio.sleep(4)
                    
                    c = await page.content()
                    if 'captchalogin' not in c and 'colsmenu' in c:
                        log("Vượt qua Captcha thành công!")
                        break

            await asyncio.sleep(2)
            # Mở menu Comments Hearts
            STATUS["current_status"] = "Đang chọn Comments Hearts..."
            chearts_btn = page.locator(".t-chearts-button")
            if await chearts_btn.count() > 0:
                await chearts_btn.first.click(force=True)
            await asyncio.sleep(2)

            await page.evaluate("""() => {
                document.querySelectorAll('.colsmenu').forEach(e => e.classList.add('nonec'));
                const p = document.querySelector('.t-chearts-menu');
                if (p) { p.classList.remove('nonec'); p.style.display = 'block'; }
            }""")

            # Vòng lặp gửi
            round_idx = 0
            while True:
                round_idx += 1
                STATUS["current_status"] = f"Đang buff lượt #{round_idx}..."
                log(f"--- Bắt đầu lượt #{round_idx} ---")
                
                try:
                    input_box = page.locator('.t-chearts-menu input[type="search"], .t-chearts-menu input[type="text"]').first
                    await input_box.fill(self.target_url)
                    await asyncio.sleep(0.5)
                    
                    search_btn = page.locator('.t-chearts-menu button[type="submit"]').first
                    await search_btn.click(force=True)
                    await input_box.press("Enter")
                    log("Đã bấm Search video, chờ danh sách bình luận...")

                    action_clicked = False
                    for _ in range(16):
                        await asyncio.sleep(1)

                        # Chọn limit 50 nếu có dropdown (Comments Hearts max 50)
                        selects = page.locator('.t-chearts-menu select')
                        if await selects.count() > 0:
                            sel = selects.first
                            opts = await sel.locator('option').all_inner_texts()
                            selected = False
                            for target_val in ['50', '25', '10']:
                                for o in opts:
                                    if target_val in o:
                                        await sel.select_option(label=o)
                                        log(f"Đã chọn limit: {o}")
                                        selected = True
                                        break
                                if selected:
                                    break

                        # Tìm các nút bình luận
                        result_btns = page.locator('#c2VuZC9mb2xsb3dlcnNfdGlrdG9r button, .t-chearts-menu form ~ div button')
                        btn_count = await result_btns.count()

                        if btn_count > 0:
                            target_btn = None
                            for i in range(btn_count):
                                btn = result_btns.nth(i)
                                txt = (await btn.inner_text()).strip()
                                if 'search' in txt.lower():
                                    continue

                                parent_text = await btn.evaluate("b => b.parentElement ? (b.parentElement.innerText || '') : ''")
                                p_lower = parent_text.lower()

                                match_kw = True if not KEYWORD else (KEYWORD in p_lower)
                                match_user = True if not USERNAME else (USERNAME in p_lower)

                                if match_kw and match_user:
                                    if i >= COMMENT_INDEX:
                                        target_btn = btn
                                        log(f"Khớp bình luận: '{parent_text.strip()[:50]}...'")
                                        break

                            if not target_btn and btn_count > 0:
                                target_btn = result_btns.first

                            if target_btn:
                                log("Bấm nút gửi Tim cho bình luận!")
                                await target_btn.click(force=True)
                                action_clicked = True
                                break

                        if action_clicked:
                            break

                    if action_clicked:
                        STATUS["total_sent"] += 1
                        log(f"💖 Gửi Tim Bình Luận thành công! Tổng: {STATUS['total_sent']}")
                        await asyncio.sleep(4)

                    # Cooldown
                    STATUS["current_status"] = "Đang chờ Cooldown..."
                    log("Đang theo dõi Cooldown...")
                    empty_count = 0
                    last_logged_time = ""
                    for c_step in range(90):
                        await asyncio.sleep(3)
                        text = await page.evaluate("() => document.querySelector('.t-chearts-menu')?.innerText || document.body.innerText || ''")
                        
                        match_min_sec = re.search(r'(\d+)\s*m(?:inutes?)?\s*\(?s?\)?\s*(\d+)\s*s(?:econds?)?', text, re.I)
                        match_sec_only = re.search(r'(\d+)\s*s(?:econds?)?', text, re.I)
                        match_colon = re.search(r'(\d{1,2})\s*:\s*(\d{2})', text)

                        time_str = None
                        if match_min_sec:
                            time_str = f"{match_min_sec.group(1)}m {match_min_sec.group(2)}s"
                        elif match_colon:
                            time_str = f"{match_colon.group(1)}:{match_colon.group(2)}"
                        elif match_sec_only and any(w in text.lower() for w in ['wait', 'seconds', 'next submit']):
                            time_str = f"{match_sec_only.group(1)}s"

                        if time_str:
                            STATUS["cooldown"] = time_str
                            STATUS["current_status"] = f"Đang chờ Cooldown ({time_str})"
                            empty_count = 0
                            if c_step % 6 == 0 and time_str != last_logged_time:
                                log(f"⏳ Cooldown còn: {time_str}")
                                last_logged_time = time_str
                        else:
                            empty_count += 1
                            if empty_count >= 2:
                                STATUS["cooldown"] = "0s (Sẵn sàng)"
                                STATUS["current_status"] = "Sẵn sàng cho lượt tiếp theo"
                                log("✅ Hết thời gian Cooldown! Bắt đầu lượt buff mới.")
                                break

                except Exception as e:
                    log(f"Lỗi: {e}")
                    await asyncio.sleep(8)

def start_bot_thread():
    bot = ZefoyCommentsHeartsBot(TARGET_URL, DEFAULT_GEMINI_KEY)
    asyncio.run(bot.run())

if __name__ == "__main__":
    t = threading.Thread(target=start_bot_thread, daemon=True)
    t.start()
    start_web_server()
