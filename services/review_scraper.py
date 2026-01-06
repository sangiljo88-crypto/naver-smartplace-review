from dataclasses import dataclass
from typing import List, Optional
import asyncio
import re

@dataclass
class Review:
    id: str
    author: str
    rating: int
    content: str
    date: str
    visit_count: str
    photos: List[str]
    has_reply: bool
    reply_content: Optional[str]
    reply_date: Optional[str]

class ReviewScraper:
    def __init__(self, context):
        """
        Args:
            context: Playwright 브라우저 컨텍스트 (로그인된 상태)
        """
        self.context = context
        
    async def get_reviews(
        self, 
        business_id: str, 
        filter_type: str = "all",  # all, no_reply, has_reply
        sort_by: str = "recent",   # recent, rating
        limit: int = 30
    ) -> List[Review]:
        """
        리뷰 목록 가져오기
        """
        page = None
        reviews = []
        
        try:
            page = await self.context.new_page()
            
            # 리뷰 페이지 URL
            url = f"https://new.smartplace.naver.com/biz/{business_id}/review/visitor"
            
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)
            
            # 더보기 버튼 클릭 (최대 3번)
            for _ in range(3):
                try:
                    more_btn = await page.query_selector('button[class*="more"], a[class*="more"], [class*="더보기"]')
                    if more_btn:
                        await more_btn.click()
                        await page.wait_for_timeout(1000)
                    else:
                        break
                except:
                    break
            
            # 리뷰 요소 찾기
            review_selectors = [
                'li[class*="review"]',
                '[class*="review-item"]',
                '[class*="ReviewItem"]',
                'article[class*="review"]',
                '[data-review-id]'
            ]
            
            review_elements = []
            for selector in review_selectors:
                review_elements = await page.query_selector_all(selector)
                if review_elements:
                    break
            
            # 리뷰가 없으면 다른 방법 시도
            if not review_elements:
                # 전체 HTML에서 파싱
                content = await page.content()
                reviews = self._parse_reviews_from_html(content, limit)
            else:
                # 요소에서 파싱
                for elem in review_elements[:limit]:
                    try:
                        review = await self._parse_review_element(elem)
                        if review:
                            # 필터 적용
                            if filter_type == "no_reply" and review.has_reply:
                                continue
                            if filter_type == "has_reply" and not review.has_reply:
                                continue
                            reviews.append(review)
                    except Exception as e:
                        print(f"리뷰 파싱 오류: {e}")
                        continue
            
        except Exception as e:
            print(f"리뷰 조회 오류: {e}")
        finally:
            if page:
                await page.close()
        
        return reviews
    
    async def _parse_review_element(self, elem) -> Optional[Review]:
        """리뷰 요소에서 데이터 추출"""
        try:
            # ID
            review_id = await elem.get_attribute("data-review-id")
            if not review_id:
                review_id = await elem.get_attribute("data-id")
            if not review_id:
                # 임의 ID 생성
                import hashlib
                content = await elem.inner_text()
                review_id = hashlib.md5(content.encode()).hexdigest()[:12]
            
            # 작성자
            author = "익명"
            for sel in ['.author', '.nickname', '[class*="user"]', '[class*="name"]', 'strong']:
                author_elem = await elem.query_selector(sel)
                if author_elem:
                    author = await author_elem.inner_text()
                    break
            
            # 별점
            rating = 5
            for sel in ['.rating', '[class*="star"]', '[class*="score"]']:
                rating_elem = await elem.query_selector(sel)
                if rating_elem:
                    rating_text = await rating_elem.inner_text()
                    nums = re.findall(r'\d+', rating_text)
                    if nums:
                        rating = min(int(nums[0]), 5)
                    break
            
            # 별 이미지 개수로 별점 추출
            if rating == 5:
                stars = await elem.query_selector_all('[class*="star"][class*="on"], [class*="fill"]')
                if stars:
                    rating = min(len(stars), 5)
            
            # 내용
            content = ""
            for sel in ['.content', '.review-text', '[class*="txt"]', '[class*="content"]', 'p']:
                content_elem = await elem.query_selector(sel)
                if content_elem:
                    content = await content_elem.inner_text()
                    if len(content) > 10:
                        break
            
            # 날짜
            date = ""
            for sel in ['.date', 'time', '[class*="date"]', '[class*="time"]']:
                date_elem = await elem.query_selector(sel)
                if date_elem:
                    date = await date_elem.inner_text()
                    break
            
            # 방문 횟수
            visit_count = ""
            for sel in ['[class*="visit"]', '[class*="count"]']:
                visit_elem = await elem.query_selector(sel)
                if visit_elem:
                    visit_count = await visit_elem.inner_text()
                    break
            
            # 사진
            photos = []
            photo_elems = await elem.query_selector_all('img[src*="review"], img[src*="photo"]')
            for photo in photo_elems[:3]:
                src = await photo.get_attribute("src")
                if src:
                    photos.append(src)
            
            # 사장님 답글
            has_reply = False
            reply_content = None
            reply_date = None
            
            for sel in ['.owner-reply', '[class*="reply"]', '[class*="answer"]', '[class*="response"]']:
                reply_elem = await elem.query_selector(sel)
                if reply_elem:
                    reply_text = await reply_elem.inner_text()
                    if reply_text and len(reply_text) > 5:
                        has_reply = True
                        reply_content = reply_text
                        
                        # 답글 날짜
                        reply_date_elem = await reply_elem.query_selector('time, [class*="date"]')
                        if reply_date_elem:
                            reply_date = await reply_date_elem.inner_text()
                        break
            
            return Review(
                id=review_id,
                author=author.strip()[:20],
                rating=rating,
                content=content.strip()[:500],
                date=date.strip(),
                visit_count=visit_count.strip(),
                photos=photos,
                has_reply=has_reply,
                reply_content=reply_content,
                reply_date=reply_date
            )
        except Exception as e:
            print(f"리뷰 요소 파싱 오류: {e}")
            return None
    
    def _parse_reviews_from_html(self, html: str, limit: int) -> List[Review]:
        """HTML에서 리뷰 파싱 (BeautifulSoup 사용)"""
        from bs4 import BeautifulSoup
        
        reviews = []
        soup = BeautifulSoup(html, 'lxml')
        
        # 리뷰 컨테이너 찾기
        review_containers = soup.select('li[class*="review"], [class*="review-item"], article')
        
        for i, container in enumerate(review_containers[:limit]):
            try:
                # ID
                review_id = container.get('data-review-id') or container.get('data-id') or f"review_{i}"
                
                # 작성자
                author_elem = container.select_one('[class*="name"], [class*="author"], strong')
                author = author_elem.get_text(strip=True) if author_elem else "익명"
                
                # 별점
                rating = 5
                star_elems = container.select('[class*="star"][class*="on"], [class*="fill"]')
                if star_elems:
                    rating = min(len(star_elems), 5)
                
                # 내용
                content_elem = container.select_one('[class*="content"], [class*="txt"], p')
                content = content_elem.get_text(strip=True) if content_elem else ""
                
                # 날짜
                date_elem = container.select_one('time, [class*="date"]')
                date = date_elem.get_text(strip=True) if date_elem else ""
                
                # 답글 확인
                reply_elem = container.select_one('[class*="reply"], [class*="answer"]')
                has_reply = reply_elem is not None
                reply_content = reply_elem.get_text(strip=True) if reply_elem else None
                
                if content:
                    reviews.append(Review(
                        id=review_id,
                        author=author[:20],
                        rating=rating,
                        content=content[:500],
                        date=date,
                        visit_count="",
                        photos=[],
                        has_reply=has_reply,
                        reply_content=reply_content,
                        reply_date=None
                    ))
            except:
                continue
        
        return reviews
    
    async def get_review_stats(self, business_id: str) -> dict:
        """리뷰 통계 가져오기"""
        page = None
        stats = {
            'total': 0,
            'average_rating': 0.0,
            'no_reply_count': 0
        }
        
        try:
            page = await self.context.new_page()
            url = f"https://new.smartplace.naver.com/biz/{business_id}/review"
            
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(1000)
            
            # 총 리뷰 수
            total_elem = await page.query_selector('[class*="total"], [class*="count"]')
            if total_elem:
                total_text = await total_elem.inner_text()
                nums = re.findall(r'\d+', total_text)
                if nums:
                    stats['total'] = int(nums[0])
            
        except Exception as e:
            print(f"통계 조회 오류: {e}")
        finally:
            if page:
                await page.close()
        
        return stats
