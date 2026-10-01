import asyncio
import os
import re
import time
import base64
import requests
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from playwright.async_api import async_playwright

ZEFOY_URL = "https://zefoy.com/"
DEFAULT_GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3.5-flash-lite"
TARGET_URL = os.getenv("TIKTOK_URL", "https://vt.tiktok.com/ZS9DYddHW9abm-CnX9Q/")
KEYWORD = os.getenv("COMMENT_KEYWORD", "ok").lower().strip() or None
USERNAME = os.getenv("COMMENT_USERNAME", "dtt_027").lower().strip() or None
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
    if len(STATUS["logs"]) > 50:
        STATUS["logs"].pop(0)
    STATUS["last_update"] = timestamp

def resolve_tiktok_url(url):
    """Tự động resolve link rút gọn vt.tiktok.com sang link video đầy đủ"""
    if not url:
        return url
    if "vt.tiktok.com" in url or "vm.tiktok.com" in url:
        try:
            r = requests.head(url, allow_redirects=True, timeout=10, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            clean = r.url.split('?')[0]
            log(f"Đã giải mã link rút gọn: {url} -> {clean}")
            return clean
        except Exception as e:
            log(f"Lỗi giải mã link rút gọn: {e}")
    return url.split('?')[0]

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
        <p><b>Mục tiêu buff:</b> <span style="color: #e3b341;">{filter_desc} (User: {USERNAME}, Keyword: {KEYWORD})</span></p>
        <p><b>Limit mỗi lượt:</b> <span style="color: #56d364; font-weight: bold;">50 Tim</span></p>
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
        self.raw_target_url = target_url
        self.target_url = resolve_tiktok_url(target_url)
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
                headless=False, # Chạy trong Xvfb ảo
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

            # Giải Captcha tự động
            content = await page.content()
            if 'captchalogin' in content:
                STATUS["current_status"] = "Đang giải Captcha bằng AI..."
                for attempt in range(1, 6):
                    # Xóa modal quảng cáo nếu có che khuất
                    await page.evaluate("""() => {
                        document.querySelectorAll('.modal, .modal-backdrop').forEach(el => el.remove());
                        document.body.classList.remove('modal-open');
                    }""")
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
                    await page.locator('button.submit-captcha, button[type="submit"]').first.click(force=True)
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
                    # Đảm bảo link đã được resolve
                    if "vt.tiktok.com" in self.target_url or "vm.tiktok.com" in self.target_url:
                        self.target_url = resolve_tiktok_url(self.target_url)

                    input_box = page.locator('.t-chearts-menu input[type="search"], .t-chearts-menu input[type="text"]').first
                    await input_box.fill("")
                    await asyncio.sleep(0.2)
                    await input_box.fill(self.target_url)
                    await asyncio.sleep(0.5)
                    
                    search_btn = page.locator('.t-chearts-menu button[type="submit"]').first
                    await search_btn.click(force=True)
                    log(f"Đã bấm Search video: {self.target_url}")
                    await asyncio.sleep(3)

                    # Bước 1: Kiểm tra xem có đang bị Cooldown không
                    for _ in range(75):
                        menu_text = await page.locator('.t-chearts-menu').inner_text()
                        if "Please wait" in menu_text:
                            m = re.search(r'Please wait\s+(\d+\s+minute\(s\)\s+\d+\s+second\(s\))', menu_text)
                            c_str = m.group(1) if m else "..."
                            STATUS["cooldown"] = c_str
                            STATUS["current_status"] = f"Đang chờ Cooldown ({c_str})"
                            await asyncio.sleep(4)
                        else:
                            break

                    # Sau khi hết Cooldown, kiểm tra nút số lượng comment (#c2VuZC9mb2xsb3dlcnNfdGlrdG9r button.wbutton)
                    count_btn = page.locator('#c2VuZC9mb2xsb3dlcnNfdGlrdG9r button.wbutton, #c2VuZC9mb2xsb3dlcnNfdGlrdG9r form button')
                    if await count_btn.count() == 0:
                        log("Bấm Search để nạp nút danh sách bình luận...")
                        await search_btn.click(force=True)
                        await asyncio.sleep(5)

                    action_clicked = False
                    if await count_btn.count() > 0:
                        count_text = (await count_btn.first.inner_text()).strip()
                        log(f"Tìm thấy nút mở bình luận ({count_text}), đang bấm mở...")
                        await count_btn.first.click(force=True)
                        await asyncio.sleep(5)

                        # Tìm danh sách comment
                        comment_items = page.locator('#c2VuZC9mb2xsb3dlcnNfdGlrdG9r li.list-group-item')
                        item_count = await comment_items.count()
                        log(f"Đã tải {item_count} bình luận vào danh sách")

                        target_item = None
                        for i in range(item_count):
                            item = comment_items.nth(i)
                            t = (await item.inner_text()).lower()
                            match_kw = True if not KEYWORD else (KEYWORD.lower() in t)
                            match_user = True if not USERNAME else (USERNAME.lower() in t)
                            if match_kw and match_user:
                                target_item = item
                                log(f"Khớp bình luận: {(await item.inner_text()).strip()[:40]}...")
                                break

                        if not target_item and item_count > 0:
                            target_item = comment_items.first
                            log(f"Chọn bình luận đầu tiên: {(await target_item.inner_text()).strip()[:40]}...")

                        if target_item:
                            # Chọn limit 50
                            sel = target_item.locator('select#selectlimit, select[name="select_lmt"]')
                            if await sel.count() > 0:
                                try:
                                    await sel.select_option(value="50")
                                    log("Đã chọn mức Limit: 50 Tim")
                                except Exception:
                                    pass
                                await asyncio.sleep(0.5)

                            # Bấm nút gửi tim
                            heart_btn = target_item.locator('button.wbutton, button[type="submit"]')
                            if await heart_btn.count() > 0:
                                log("💖 Đang bấm nút gửi 50 Tim vào bình luận...")
                                await heart_btn.first.click(force=True)
                                action_clicked = True
                                await asyncio.sleep(4)

                    if action_clicked:
                        STATUS["total_sent"] += 1
                        log(f"💖 Gửi 50 Tim Bình Luận thành công! Tổng số lượt: {STATUS['total_sent']}")
                        await asyncio.sleep(3)

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

def main():
    api_key = DEFAULT_GEMINI_KEY
    if not api_key:
        print("[!] Lỗi: Chưa cung cấp GEMINI_API_KEY trong biến môi trường!")
        return

    # Chạy Web server giám sát trên thread riêng
    t = Thread(target=start_web_server, daemon=True)
    t.start()

    # Chạy bot buff comments hearts
    bot = ZefoyCommentsHeartsBot(TARGET_URL, api_key)
    asyncio.run(bot.run())

if __name__ == "__main__":
    main()
