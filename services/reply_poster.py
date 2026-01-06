import asyncio
from typing import Optional

class ReplyPoster:
    def __init__(self, context):
        """
        Args:
            context: Playwright 브라우저 컨텍스트 (로그인된 상태)
        """
        self.context = context
    
    async def post_reply(
        self,
        business_id: str,
        review_id: str,
        reply_content: str
    ) -> dict:
        """
        리뷰에 답글 등록
        
        Args:
            business_id: 업체 ID
            review_id: 리뷰 ID
            reply_content: 답글 내용
            
        Returns:
            dict: {'success': bool, 'message': str}
        """
        page = None
        
        try:
            page = await self.context.new_page()
            
            # 리뷰 페이지로 이동
            url = f"https://new.smartplace.naver.com/biz/{business_id}/review/visitor"
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)
            
            # 해당 리뷰 찾기
            review_elem = await page.query_selector(f'[data-review-id="{review_id}"], [data-id="{review_id}"]')
            
            if not review_elem:
                # 리뷰 ID로 찾지 못하면 전체 리뷰 목록에서 찾기
                review_elems = await page.query_selector_all('li[class*="review"], [class*="review-item"]')
                if review_elems:
                    review_elem = review_elems[0]  # 첫 번째 리뷰 선택
            
            if not review_elem:
                return {'success': False, 'message': '리뷰를 찾을 수 없습니다. 페이지를 새로고침 해주세요.'}
            
            # 답글 달기 버튼 찾기
            reply_btn_selectors = [
                'button[class*="reply"]',
                'a[class*="reply"]',
                '[class*="답글"]',
                'button:has-text("답글")',
                '[class*="write"]'
            ]
            
            reply_btn = None
            for selector in reply_btn_selectors:
                reply_btn = await review_elem.query_selector(selector)
                if reply_btn:
                    break
            
            if not reply_btn:
                # 페이지 전체에서 찾기
                for selector in reply_btn_selectors:
                    reply_btn = await page.query_selector(selector)
                    if reply_btn:
                        break
            
            if not reply_btn:
                return {'success': False, 'message': '답글 버튼을 찾을 수 없습니다. 이미 답글이 달려있을 수 있습니다.'}
            
            # 답글 버튼 클릭
            await reply_btn.click()
            await page.wait_for_timeout(1000)
            
            # 답글 입력창 찾기
            textarea_selectors = [
                'textarea[class*="reply"]',
                'textarea[class*="input"]',
                '[class*="reply"] textarea',
                'textarea',
                '[contenteditable="true"]'
            ]
            
            textarea = None
            for selector in textarea_selectors:
                textarea = await page.query_selector(selector)
                if textarea:
                    break
            
            if not textarea:
                return {'success': False, 'message': '답글 입력창을 찾을 수 없습니다.'}
            
            # 답글 입력
            await textarea.fill(reply_content)
            await page.wait_for_timeout(500)
            
            # 등록 버튼 찾기 및 클릭
            submit_selectors = [
                'button[type="submit"]',
                'button[class*="submit"]',
                'button[class*="register"]',
                'button:has-text("등록")',
                'button:has-text("완료")',
                '[class*="submit"]'
            ]
            
            submit_btn = None
            for selector in submit_selectors:
                submit_btn = await page.query_selector(selector)
                if submit_btn:
                    break
            
            if submit_btn:
                await submit_btn.click()
                await page.wait_for_timeout(2000)
                return {'success': True, 'message': '답글이 등록되었습니다! 🎉'}
            else:
                return {'success': False, 'message': '등록 버튼을 찾을 수 없습니다. 수동으로 등록해주세요.'}
                
        except Exception as e:
            return {'success': False, 'message': f'오류 발생: {str(e)}'}
        finally:
            if page:
                await page.close()
    
    async def post_bulk_replies(
        self,
        business_id: str,
        replies: list,
        delay: float = 5.0
    ) -> list:
        """
        여러 답글 일괄 등록
        
        Args:
            business_id: 업체 ID
            replies: [{'review_id': str, 'content': str}, ...]
            delay: 요청 간 대기 시간 (초) - 봇 탐지 방지
            
        Returns:
            list: [{'review_id': str, 'success': bool, 'message': str}, ...]
        """
        results = []
        
        for i, reply in enumerate(replies):
            result = await self.post_reply(
                business_id=business_id,
                review_id=reply['review_id'],
                reply_content=reply['content']
            )
            result['review_id'] = reply['review_id']
            results.append(result)
            
            # 봇 탐지 방지를 위한 딜레이
            if i < len(replies) - 1:
                await asyncio.sleep(delay)
        
        return results
