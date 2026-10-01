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
            print(f"[*] Đã giải mã link rút gọn: {url} -> {clean}")
            return clean
        except Exception as e:
            print(f"[!] Lỗi giải mã link: {e}")
    return url.split('?')[0]

class ZefoyCommentsHeartsBot:
    def __init__(self, target_url, api_key=None, keyword=None, username=None, comment_index=0, loops=0):
        self.raw_target_url = target_url
        self.target_url = resolve_tiktok_url(target_url)
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
        """Điền link video -> Bấm Search -> Bấm nút số lượng bình luận -> Chọn bình luận mục tiêu -> Bấm nút Tim"""
        try:
            if "vt.tiktok.com" in self.target_url or "vm.tiktok.com" in self.target_url:
                self.target_url = resolve_tiktok_url(self.target_url)

            input_box = page.locator(
                '.t-chearts-menu input[type="search"], .t-chearts-menu input[placeholder*="URL"], .t-chearts-menu input[type="text"]'
            )
            if await input_box.count() == 0:
                print("[!] Không tìm thấy ô nhập link trong Comments Hearts!")
                return "retry"

            target_input = input_box.first
            await target_input.fill("")
            await asyncio.sleep(0.3)
            await target_input.fill(self.target_url)
            print(f"[*] Đã điền link video TikTok: {self.target_url}")
            await asyncio.sleep(0.5)

            # Bấm Search
            print("[*] Đang bấm nút Search...")
            search_btn = page.locator(
                '.t-chearts-menu button[type="submit"], .t-chearts-menu button:has-text("Search")'
            ).first
            await search_btn.click(force=True)
            await asyncio.sleep(3)

            # Kiểm tra nếu Zefoy đang trong Cooldown
            panel_text = await page.locator('.t-chearts-menu').inner_text()
            if "please wait" in panel_text.lower():
                print("[⏳] Phát hiện thông báo Cooldown đang đếm ngược.")
                return "cooldown"

            # Kiểm tra nút số lượng bình luận (ví dụ: ' 2' với icon fa-comments)
            count_btn = page.locator('#c2VuZC9mb2xsb3dlcnNfdGlrdG9r button')
            if await count_btn.count() == 0:
                print("[*] Bấm Search để nạp nút bình luận...")
                await search_btn.click(force=True)
                await asyncio.sleep(5)
                count_btn = page.locator('#c2VuZC9mb2xsb3dlcnNfdGlrdG9r button')

            action_clicked = False
            if await count_btn.count() > 0:
                c_text = (await count_btn.first.inner_text()).strip()
                print(f"[*] Tìm thấy nút mở danh sách bình luận ({c_text}), đang bấm mở...")
                await count_btn.first.click(force=True)
                await page.evaluate("""() => {
                    const btn = document.querySelector('#c2VuZC9mb2xsb3dlcnNfdGlrdG9r button');
                    if (btn) {
                        btn.click();
                        const f = btn.closest('form');
                        if (f && f.requestSubmit) f.requestSubmit(btn);
                    }
                }""")
                
                # Chờ danh sách comment tải xong (select hoặc heart button xuất hiện)
                for _ in range(15):
                    await asyncio.sleep(1)
                    has_sel = await page.locator('#c2VuZC9mb2xsb3dlcnNfdGlrdG9r select').count() > 0
                    has_heart = await page.locator('#c2VuZC9mb2xsb3dlcnNfdGlrdG9r button:has(i), #c2VuZC9mb2xsb3dlcnNfdGlrdG9r button.btn-primary').count() > 0
                    if has_sel or has_heart:
                        break

                items = page.locator('#c2VuZC9mb2xsb3dlcnNfdGlrdG9r form, #c2VuZC9mb2xsb3dlcnNfdGlrdG9r .card, #c2VuZC9mb2xsb3dlcnNfdGlrdG9r div:has(select)')
                item_count = await items.count()
                print(f"[*] Đã phát hiện {item_count} khối bình luận/form trong danh sách")

                target_container = None
                if item_count > 1:
                    for i in range(item_count):
                        it = items.nth(i)
                        t = (await it.inner_text()).lower()
                        match_keyword = True if not self.keyword else (self.keyword in t)
                        match_username = True if not self.username else (self.username in t)
                        if match_keyword and match_username:
                            if i >= self.comment_index:
                                target_container = it
                                print(f"[🎯] Đã khớp bình luận mục tiêu: {(await it.inner_text()).strip()[:60]}...")
                                break

                if not target_container:
                    if item_count > 0:
                        target_container = items.first
                    else:
                        target_container = page.locator('#c2VuZC9mb2xsb3dlcnNfdGlrdG9r')

                # Kiểm tra phân trang nếu chưa khớp
                target_text = (await target_container.inner_text()).lower()
                match_keyword = True if not self.keyword else (self.keyword in target_text)
                match_username = True if not self.username else (self.username in target_text)
                if not (match_keyword and match_username):
                    next_btn = page.locator('#c2VuZC9mb2xsb3dlcnNfdGlrdG9r a:has-text(">"), #c2VuZC9mb2xsb3dlcnNfdGlrdG9r button:has-text(">"), #c2VuZC9mb2xsb3dlcnNfdGlrdG9r .pagination a')
                    if await next_btn.count() > 0:
                        print("[*] Bình luận hiện tại chưa khớp, đang chuyển trang tiếp...")
                        await next_btn.last.click(force=True)
                        await asyncio.sleep(3)

                # Chọn limit 50
                sel = page.locator('#c2VuZC9mb2xsb3dlcnNfdGlrdG9r select').first
                if await sel.count() > 0:
                    try:
                        await sel.select_option("50")
                        print("[*] Đã chọn limit: 50")
                    except Exception:
                        try:
                            await sel.select_option(label="50")
                            print("[*] Đã chọn limit (label): 50")
                        except Exception:
                            pass
                    await asyncio.sleep(0.5)

                # Bấm nút gửi tim
                heart_btn = target_container.locator('button:has(i), button.btn-primary, button[type="submit"], button').first
                if await heart_btn.count() > 0:
                    print("[🔥] Đang bấm nút gửi 50 Tim cho bình luận...")
                    await heart_btn.click(force=True)
                    action_clicked = True
                    await asyncio.sleep(4)

            if action_clicked:
                return "sent"

            final_text = await page.locator('.t-chearts-menu').inner_text()
            if 'please wait' in final_text.lower():
                return "cooldown"

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
