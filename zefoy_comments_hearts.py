#!/usr/bin/env python3
"""
⚡ TikTok Zefoy Comments Hearts Booster (Full Auto: Gemini Vision Captcha Solver) ⚡

Chuyên dụng buff Tim Bình Luận (Comments Hearts) trên Zefoy.com:
1. Tự động giải Captcha bằng Gemini Vision AI (100% không cần can thiệp).
2. Tự động chọn dịch vụ Comments Hearts (.t-chearts-button).
3. Nhập link video TikTok chứa bình luận cần buff -> Bấm Search.
4. Tự động quét danh sách bình luận trả về:
   - Hỗ trợ chọn bình luận theo từ khóa (--keyword) hoặc tên tài khoản (--username).
   - Mặc định buff cho bình luận đầu tiên nếu không chỉ định.
5. Tự động kích hoạt nút gửi Tim cho bình luận đó.
6. Tự động theo dõi Cooldown đếm ngược và lặp lại liên tục.
"""

import argparse
import asyncio
import base64
import os
import re
import sys
import time
import requests
from playwright.async_api import async_playwright

ZEFOY_URL = "https://zefoy.com/"
DEFAULT_GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3.5-flash-lite"

class ZefoyCommentsHeartsBot:
    def __init__(self, target_url, api_key=None, keyword=None, username=None, comment_index=0, loops=0):
        self.target_url = target_url
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", DEFAULT_GEMINI_KEY)
        self.keyword = keyword.lower() if keyword else None
        self.username = username.lower() if username else None
        self.comment_index = comment_index
        self.loops = loops
        self.total_sent = 0
        self.start_time = time.time()

    def solve_captcha_api(self, image_bytes):
        """Gửi ảnh Captcha qua Gemini 3.5 Flash Lite để nhận diện text"""
        b64_img = base64.b64encode(image_bytes).decode('utf-8')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={self.api_key}"
        
        prompt = (
            "This is a text captcha image. Read the word or letters shown in this image. "
            "Output ONLY the letters in lowercase, with no spaces, no punctuation, and no markdown."
        )
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": "image/png",
                            "data": b64_img
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 20
            }
        }
        
        try:
            res = requests.post(url, json=payload, timeout=12)
            if res.status_code == 200:
                data = res.json()
                raw_text = data['candidates'][0]['content']['parts'][0]['text']
                cleaned = re.sub(r'[^a-zA-Z]', '', raw_text).lower().strip()
                return cleaned
            else:
                print(f"[!] Gemini API Error ({res.status_code}): {res.text[:150]}")
        except Exception as e:
            print(f"[!] Lỗi gọi Gemini API: {e}")
        return None

    async def auto_solve_captcha(self, page):
        """Tự động phát hiện và giải Captcha qua Gemini AI"""
        print("\n[*] 🤖 Đang kích hoạt bộ giải Captcha AI tự động (Gemini Vision)...")

        for attempt in range(1, 6):
            print(f"[*] Thử giải Captcha lần #{attempt}...")
            captcha_img = page.locator('#captcha-img')
            try:
                await captcha_img.wait_for(state="visible", timeout=12000)
                await asyncio.sleep(1)
            except Exception:
                content = await page.content()
                if 'captchalogin' not in content:
                    print("[✅] Đã vượt qua Captcha!")
                    return True

            img_bytes = await captcha_img.screenshot()
            text = self.solve_captcha_api(img_bytes)
            if not text:
                print("[!] AI chưa nhận diện được chữ. Đang tải lại Captcha...")
                await self._refresh_captcha(page)
                continue

            print(f"[🤖 Gemini AI]: Nhận diện từ Captcha = '{text}'")

            input_cap = page.locator('input[name="captchalogin"]')
            await input_cap.click()
            await input_cap.fill("")
            await input_cap.fill(text)
            await asyncio.sleep(0.5)

            submit_btn = page.locator('button.submit-captcha, button[type="submit"]')
            if await submit_btn.count() > 0:
                await submit_btn.first.click()
            else:
                await input_cap.press("Enter")

            await asyncio.sleep(4)

            content = await page.content()
            if 'captchalogin' not in content and 'colsmenu' in content:
                print(f"[✅ THÀNH CÔNG] Đã tự động vượt Captcha bằng AI ở lần #{attempt}!")
                return True

            print("[!] Captcha không chính xác hoặc Zefoy yêu cầu thử lại. Đang đổi mã...")
            await self._refresh_captcha(page)

        print("[!] Không vượt qua được Captcha sau 5 lần thử.")
        return False

    async def _refresh_captcha(self, page):
        try:
            refresh_btn = page.locator('.refresh-capthca-btn-new, a[onclick*="ebot"]')
            if await refresh_btn.count() > 0:
                await refresh_btn.first.click(force=True)
            await asyncio.sleep(2)
        except Exception:
            pass

    async def run(self):
        print("="*65)
        print("  ⚡ ZEFOY COMMENTS HEARTS AUTO-BOOSTER (GEMINI VISION) ⚡")
        print(f"  Target Video   : {self.target_url}")
        print(f"  Target Keyword : {self.keyword or 'Mặc định (bình luận đầu tiên)'}")
        print(f"  Target User    : {self.username or 'Không chỉ định'}")
        print(f"  Target Loop    : {'Vô hạn' if self.loops == 0 else f'{self.loops} lần'}")
        print("="*65)

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-infobars'
                ]
            )

            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            )

            page = await context.new_page()
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => false });")

            print("\n[*] Đang truy cập Zefoy.com...")
            await page.goto(ZEFOY_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # BƯỚC 1: GIẢI CAPTCHA AI
            content = await page.content()
            if 'captchalogin' in content:
                passed = await self.auto_solve_captcha(page)
                if not passed:
                    print("[!] Không thể tiếp tục do chưa vượt qua Captcha.")
                    await browser.close()
                    return

            await asyncio.sleep(2)

            # BƯỚC 2: MỞ MENU COMMENTS HEARTS
            print("\n[*] Đang mở menu Comments Hearts...")
            chearts_btn = page.locator(".t-chearts-button")
            if await chearts_btn.count() > 0:
                await chearts_btn.first.click(force=True)
                print("[✅] Đã click nút Comments Hearts!")
            else:
                await page.evaluate("""() => {
                    const btn = document.querySelector('.t-chearts-button');
                    if (btn) btn.click();
                }""")

            await asyncio.sleep(2)

            # Đảm bảo hiển thị panel form
            await page.evaluate("""() => {
                document.querySelectorAll('.colsmenu').forEach(e => e.classList.add('nonec'));
                const panel = document.querySelector('.t-chearts-menu');
                if (panel) {
                    panel.classList.remove('nonec');
                    panel.style.display = 'block';
                }
            }""")
            await asyncio.sleep(1)

            # BƯỚC 3: VÒNG LẶP AUTO BUFF TIM BÌNH LUẬN
            round_count = 0
            while True:
                if self.loops > 0 and round_count >= self.loops:
                    print(f"\n[DONE] Hoàn tất đủ {self.loops} lượt.")
                    break

                round_count += 1
                elapsed = int(time.time() - self.start_time)
                print(f"\n{'='*55}")
                print(f"  Vòng #{round_count} | Đã buff: {self.total_sent} lần | Thời gian: {elapsed}s")
                print(f"{'='*55}")

                status = await self._execute_cycle(page)

                if status == "sent":
                    self.total_sent += 1
                    print(f"\n[🔥 THÀNH CÔNG] Đã buff Tim Bình Luận thành công! (Tổng: {self.total_sent})")
                    await self._wait_cooldown(page)
                elif status == "cooldown":
                    await self._wait_cooldown(page)
                else:
                    print("[!] Thử lại chu trình sau 8 giây...")
                    await asyncio.sleep(8)

            await browser.close()

    async def _execute_cycle(self, page):
        """Điền link video -> Bấm Search -> Chọn bình luận mục tiêu -> Bấm nút Tim"""
        try:
            input_box = page.locator(
                '.t-chearts-menu input[type="search"], .t-chearts-menu input[placeholder*="URL"], .t-chearts-menu input[type="text"]'
            )
            if await input_box.count() == 0:
                print("[!] Không tìm thấy ô nhập link trong Comments Hearts!")
                return "retry"

            target_input = input_box.first
            await target_input.click()
            await target_input.fill("")
            await asyncio.sleep(0.3)
            await target_input.fill(self.target_url)
            print(f"[*] Đã điền link video TikTok: {self.target_url}")
            await asyncio.sleep(0.5)

            # Bấm Search
            print("[*] Đang bấm nút Search...")
            search_btn = page.locator(
                '.t-chearts-menu button[type="submit"], .t-chearts-menu button:has-text("Search")'
            )
            if await search_btn.count() > 0:
                await search_btn.first.click(force=True)
            else:
                await target_input.press("Enter")

            try:
                await target_input.press("Enter")
            except Exception:
                pass

            # Chờ danh sách bình luận trả về từ server Zefoy
            print("[*] Đang chờ server nạp danh sách bình luận...")
            action_clicked = False

            for wait_sec in range(16):
                await asyncio.sleep(1)

                # Kiểm tra dropdown limit nếu có (chọn max 50 cho Comments Hearts)
                selects = page.locator('.t-chearts-menu select')
                if await selects.count() > 0:
                    sel = selects.first
                    options = await sel.locator('option').all_inner_texts()
                    selected = False
                    for target_val in ['50', '25', '10']:
                        for opt in options:
                            if target_val in opt:
                                await sel.select_option(label=opt)
                                print(f"[*] Đã chọn limit: {opt}")
                                selected = True
                                break
                        if selected:
                            break

                # Tìm các bình luận và nút kích hoạt
                result_container = page.locator('#c2VuZC9mb2xsb3dlcnNfdGlrdG9r, .t-chearts-menu .card-ortlax')
                comment_btns = result_container.locator('button:not([type="submit"]):not(:has-text("Search"))')

                if await comment_btns.count() == 0:
                    comment_btns = page.locator('#c2VuZC9mb2xsb3dlcnNfdGlrdG9r button, .t-chearts-menu form ~ div button')

                btn_count = await comment_btns.count()
                if btn_count > 0:
                    print(f"[*] Tìm thấy {btn_count} nút tương ứng với các bình luận!")

                    # Trích xuất thông tin các bình luận để tìm bình luận khớp với filter
                    target_btn = None
                    target_desc = ""

                    for i in range(btn_count):
                        btn = comment_btns.nth(i)
                        txt = (await btn.inner_text()).strip()
                        if 'search' in txt.lower():
                            continue

                        # Lấy ngữ cảnh nội dung xung quanh nút (tên user hoặc text comment)
                        parent_text = await btn.evaluate("""b => {
                            let p = b.parentElement;
                            return p ? (p.innerText || '') : '';
                        }""")

                        parent_lower = parent_text.lower()

                        # Kiểm tra điều kiện lọc
                        match_keyword = True if not self.keyword else (self.keyword in parent_lower)
                        match_username = True if not self.username else (self.username in parent_lower)

                        if match_keyword and match_username:
                            if i >= self.comment_index:
                                target_btn = btn
                                target_desc = txt if txt else f"Bình luận #{i+1}"
                                print(f"[🎯] Đã khớp bình luận mục tiêu: {parent_text.strip()[:60]}...")
                                break

                    if not target_btn and btn_count > 0:
                        # Mặc định lấy nút bình luận đầu tiên
                        target_btn = comment_btns.first
                        target_desc = await target_btn.inner_text()

                    if target_btn:
                        print(f"[🔥] Đang bấm nút gửi Tim cho bình luận: '{target_desc.strip()}'...")
                        await target_btn.click(force=True)
                        action_clicked = True
                        break

                if action_clicked:
                    break

                # Kiểm tra xem có đang bị Cooldown sẵn không
                panel_text = await page.locator('.t-chearts-menu').inner_text()
                if re.search(r'please wait\s*\d+\s*(?:minute|second|s|m)', panel_text, re.I) or re.search(r'\d{1,2}\s*:\s*\d{2}', panel_text):
                    print("[⏳] Phát hiện thông báo Cooldown đang đếm ngược.")
                    return "cooldown"

            if action_clicked:
                await asyncio.sleep(4)
                return "sent"

            final_text = await page.locator('.t-chearts-menu').inner_text()
            if re.search(r'\d{1,2}\s*:\s*\d{2}', final_text) or 'please wait' in final_text.lower():
                return "cooldown"

            print("[?] Chưa thấy danh sách bình luận (có thể video không có bình luận hoặc server lag).")
            return "retry"

        except Exception as e:
            print(f"[!] Lỗi chu trình Comments Hearts: {e}")
            return "retry"

    async def _wait_cooldown(self, page):
        """Theo dõi đồng hồ đếm ngược Cooldown của Zefoy"""
        print("[⏳] Bắt đầu theo dõi thời gian Cooldown...")

        empty_checks = 0
        for _ in range(72): # Tối đa 6 phút
            await asyncio.sleep(5)

            try:
                text = await page.evaluate("""() => {
                    const panel = document.querySelector('.t-chearts-menu');
                    return panel ? panel.innerText : document.body.innerText;
                }""")

                match_min_sec = re.search(r'(\d+)\s*m(?:inutes?)?\s*(\d+)\s*s(?:econds?)?', text, re.I)
                match_sec_only = re.search(r'(\d+)\s*s(?:econds?)?', text, re.I)
                match_colon = re.search(r'(\d{1,2})\s*:\s*(\d{2})', text)

                time_str = None
                total_seconds = 0

                if match_min_sec:
                    m = int(match_min_sec.group(1))
                    s = int(match_min_sec.group(2))
                    total_seconds = m * 60 + s
                    time_str = f"{m} phút {s} giây"
                elif match_colon:
                    m = int(match_colon.group(1))
                    s = int(match_colon.group(2))
                    total_seconds = m * 60 + s
                    time_str = f"{m}:{s:02d}"
                elif match_sec_only and 'please wait' in text.lower():
                    s = int(match_sec_only.group(1))
                    total_seconds = s
                    time_str = f"{s} giây"

                if time_str and total_seconds > 0:
                    empty_checks = 0
                    print(f"\r[⏳ Cooldown]: Còn lại {time_str} ({total_seconds}s)...   ", end="", flush=True)
                else:
                    empty_checks += 1
                    if empty_checks >= 2:
                        print("\n[✅] Thời gian chờ đã kết thúc! Bắt đầu lượt buff tiếp theo.")
                        return

            except Exception:
                pass

        print("\n[*] Hết thời gian chờ tối đa. Chuẩn bị lượt mới...")


def main():
    parser = argparse.ArgumentParser(description="⚡ TikTok Zefoy Comments Hearts Booster ⚡")
    parser.add_argument("--url", required=True, help="Link bài viết/video TikTok chứa bình luận")
    parser.add_argument("--keyword", default=None, help="Từ khóa nằm trong bình luận cần buff (để lọc)")
    parser.add_argument("--username", default=None, help="Tên tài khoản của bình luận cần buff (để lọc)")
    parser.add_argument("--index", type=int, default=0, help="Vị trí bình luận nếu có nhiều kết quả (mặc định: 0 - đầu tiên)")
    parser.add_argument("--api-key", default=None, help="Gemini API Key")
    parser.add_argument("--loops", type=int, default=0, help="Số lần lặp lại (0 = vô hạn)")
    args = parser.parse_args()

    bot = ZefoyCommentsHeartsBot(
        target_url=args.url,
        api_key=args.api_key,
        keyword=args.keyword,
        username=args.username,
        comment_index=args.index,
        loops=args.loops
    )
    asyncio.run(bot.run())

if __name__ == "__main__":
    main()
