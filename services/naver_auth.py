import asyncio
from playwright.async_api import async_playwright
from typing import Optional, List, Dict
import json
import re

class NaverAuth:
    def __init__(self):
        self.cookies = None
        self.is_logged_in = False
        self.browser = None
        self.context = None
        self.playwright = None
        
    async def init_browser(self):
        """브라우저 초기화"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu'
                ]
            )
            return True
        except Exception as e:
            print(f"브라우저 초기화 실패: {e}")
            return False
        
    async def login_with_cookies(self, cookie_string: str) -> bool:
        """
        쿠키 문자열로 로그인
        
        Args:
            cookie_string: 네이버 쿠키 문자열 (NID_AUT, NID_SES 등)
            
        Returns:
            bool: 로그인 성공 여부
        """
        try:
            if not self.browser:
                await self.init_browser()
            
            # 쿠키 파싱
            cookies = self._parse_cookies(cookie_string)
            
            if not cookies:
                print("쿠키 파싱 실패")
                return False
            
            # 브라우저 컨텍스트 생성
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            # 쿠키 설정
            await self.context.add_cookies(cookies)
            
            # 로그인 검증
            page = await self.context.new_page()
            await page.goto("https://new.smartplace.naver.com/", wait_until="networkidle", timeout=30000)
            
            # 페이지 내용 확인
            content = await page.content()
            
            # 로그인 상태 확인 (여러 방법 시도)
            # 1. 로그인 버튼이 없으면 로그인 상태
            login_btn = await page.query_selector('a[href*="nidlogin"], .login-btn, [class*="login"]')
            
            # 2. 업체 정보나 사용자 정보가 있으면 로그인 상태
            user_info = await page.query_selector('[class*="user"], [class*="profile"], [class*="business"]')
            
            # 3. URL이 로그인 페이지로 리다이렉트되지 않았는지 확인
            current_url = page.url
            
            await page.close()
            
            if 'nidlogin' in current_url or 'login' in current_url.lower():
                print("로그인 페이지로 리다이렉트됨 - 쿠키 무효")
                return False
            
            self.is_logged_in = True
            self.cookies = cookies
            print("로그인 성공!")
            return True
                
        except Exception as e:
            print(f"로그인 실패: {e}")
            return False
    
    def _parse_cookies(self, cookie_string: str) -> list:
        """쿠키 문자열을 Playwright 쿠키 형식으로 변환"""
        cookies = []
        
        # 여러 형식 지원
        # 형식 1: "NID_AUT=xxx; NID_SES=xxx"
        # 형식 2: "NID_AUT=xxx\nNID_SES=xxx"
        
        cookie_string = cookie_string.replace('\n', '; ').replace('\r', '')
        
        for item in cookie_string.split(';'):
            item = item.strip()
            if '=' in item:
                name, value = item.split('=', 1)
                name = name.strip()
                value = value.strip()
                
                if name and value:
                    cookies.append({
                        'name': name,
                        'value': value,
                        'domain': '.naver.com',
                        'path': '/'
                    })
        
        return cookies
    
    async def get_business_list(self) -> List[Dict]:
        """
        등록된 업체 목록 가져오기
        
        Returns:
            list: 업체 정보 리스트 [{id, name, category}, ...]
        """
        if not self.is_logged_in or not self.context:
            return []
        
        businesses = []
        page = None
        
        try:
            page = await self.context.new_page()
            await page.goto("https://new.smartplace.naver.com/", wait_until="networkidle", timeout=30000)
            
            # 잠시 대기
            await page.wait_for_timeout(2000)
            
            # 업체 목록 찾기 (여러 선택자 시도)
            selectors = [
                '[class*="business"] [class*="item"]',
                '[class*="store"] [class*="item"]',
                '[class*="place"] [class*="item"]',
                'li[class*="item"]',
                '[data-id]'
            ]
            
            for selector in selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    for elem in elements:
                        try:
                            # ID 추출
                            bid = await elem.get_attribute("data-id")
                            if not bid:
                                href = await elem.get_attribute("href")
                                if href:
                                    match = re.search(r'/biz/(\d+)', href)
                                    if match:
                                        bid = match.group(1)
                            
                            # 이름 추출
                            name_elem = await elem.query_selector('[class*="name"], [class*="title"], h3, h4, strong')
                            name = await name_elem.inner_text() if name_elem else "업체"
                            
                            # 카테고리 추출
                            cat_elem = await elem.query_selector('[class*="category"], [class*="type"], span')
                            category = await cat_elem.inner_text() if cat_elem else ""
                            
                            if bid:
                                businesses.append({
                                    'id': bid,
                                    'name': name.strip(),
                                    'category': category.strip()
                                })
                        except:
                            continue
                    break
            
            # 업체를 찾지 못한 경우, URL에서 직접 추출 시도
            if not businesses:
                # 현재 페이지에서 업체 ID 찾기
                content = await page.content()
                matches = re.findall(r'/biz/(\d+)', content)
                if matches:
                    unique_ids = list(set(matches))[:5]  # 최대 5개
                    for bid in unique_ids:
                        businesses.append({
                            'id': bid,
                            'name': f'업체 {bid}',
                            'category': ''
                        })
            
        except Exception as e:
            print(f"업체 목록 조회 오류: {e}")
        finally:
            if page:
                await page.close()
        
        return businesses
    
    async def close(self):
        """브라우저 종료"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except:
            pass
