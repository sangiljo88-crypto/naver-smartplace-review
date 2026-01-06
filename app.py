import streamlit as st
import asyncio
import sys
import os

# 프로젝트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.naver_auth import NaverAuth
from services.review_scraper import ReviewScraper
from services.ai_generator import AIReplyGenerator, AIProvider, ReplyTone, get_tone_from_string
from services.reply_poster import ReplyPoster
from database.db import init_db, save_setting, get_setting, save_reply_history, get_reply_history

# 페이지 설정
st.set_page_config(
    page_title="네이버 플레이스 리뷰 관리",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 데이터베이스 초기화
init_db()

# 세션 상태 초기화
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'naver_auth' not in st.session_state:
    st.session_state.naver_auth = None
if 'businesses' not in st.session_state:
    st.session_state.businesses = []
if 'selected_business' not in st.session_state:
    st.session_state.selected_business = None
if 'reviews' not in st.session_state:
    st.session_state.reviews = []
if 'generated_replies' not in st.session_state:
    st.session_state.generated_replies = {}

# CSS 스타일
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1a73e8;
        margin-bottom: 1rem;
    }
    .review-card {
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 16px;
        margin: 12px 0;
        background-color: #ffffff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .rating-stars {
        color: #FFD700;
        font-size: 1.2rem;
    }
    .no-reply-badge {
        background-color: #fff3cd;
        color: #856404;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .has-reply-badge {
        background-color: #d4edda;
        color: #155724;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .owner-reply {
        background-color: #f8f9fa;
        border-left: 4px solid #1a73e8;
        padding: 12px;
        margin-top: 12px;
        border-radius: 0 8px 8px 0;
    }
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
    }
    .stat-number {
        font-size: 2rem;
        font-weight: bold;
    }
    .stat-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .stButton button {
        border-radius: 8px;
    }
    div[data-testid="stExpander"] {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ============ 헬퍼 함수 ============
def run_async(coro):
    """비동기 함수 실행 헬퍼"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# ============ 사이드바 ============
with st.sidebar:
    st.markdown("## 🏪 리뷰 관리")
    st.markdown("---")
    
    # 로그인 섹션
    st.markdown("### 🔐 로그인")
    
    if not st.session_state.logged_in:
        st.info("네이버 쿠키로 로그인하세요")
        
        with st.expander("📌 쿠키 가져오는 방법", expanded=False):
            st.markdown("""
            1. **크롬**에서 [네이버](https://naver.com) 로그인
            2. **F12** → **Application** 탭
            3. **Cookies** → `https://www.naver.com`
            4. 아래 값들 복사:
               - `NID_AUT`
               - `NID_SES`
            5. 형식: `NID_AUT=값; NID_SES=값`
            """)
        
        cookie_input = st.text_area(
            "네이버 쿠키",
            placeholder="NID_AUT=xxx; NID_SES=xxx",
            height=100,
            key="cookie_input"
        )
        
        if st.button("🔓 로그인", type="primary", use_container_width=True):
            if cookie_input:
                with st.spinner("로그인 중... 잠시만 기다려주세요"):
                    async def do_login():
                        auth = NaverAuth()
                        await auth.init_browser()
                        success = await auth.login_with_cookies(cookie_input)
                        if success:
                            businesses = await auth.get_business_list()
                            return auth, businesses
                        await auth.close()
                        return None, []
                    
                    auth, businesses = run_async(do_login())
                    
                    if auth:
                        st.session_state.logged_in = True
                        st.session_state.naver_auth = auth
                        st.session_state.businesses = businesses
                        save_setting('last_login', 'success')
                        st.success("✅ 로그인 성공!")
                        st.rerun()
                    else:
                        st.error("❌ 로그인 실패. 쿠키를 확인해주세요.")
            else:
                st.warning("쿠키를 입력해주세요.")
    else:
        st.success("✅ 로그인됨")
        if st.button("🚪 로그아웃", use_container_width=True):
            if st.session_state.naver_auth:
                run_async(st.session_state.naver_auth.close())
            st.session_state.logged_in = False
            st.session_state.naver_auth = None
            st.session_state.businesses = []
            st.session_state.selected_business = None
            st.session_state.reviews = []
            st.rerun()
    
    st.markdown("---")
    
    # 업체 선택
    if st.session_state.logged_in:
        st.markdown("### 🏬 업체 선택")
        
        if st.session_state.businesses:
            business_options = {b['name']: b for b in st.session_state.businesses}
            selected_name = st.selectbox(
                "업체",
                list(business_options.keys()),
                key="business_select"
            )
            
            if selected_name:
                selected = business_options[selected_name]
                if st.session_state.selected_business != selected:
                    st.session_state.selected_business = selected
                    st.session_state.reviews = []
        else:
            st.info("등록된 업체가 없습니다.")
            
            # 수동 입력 옵션
            manual_id = st.text_input("업체 ID 직접 입력", placeholder="예: 1234567890")
            manual_name = st.text_input("업체 이름", placeholder="예: 우리가게")
            
            if manual_id and manual_name:
                if st.button("업체 추가"):
                    st.session_state.businesses.append({
                        'id': manual_id,
                        'name': manual_name,
                        'category': ''
                    })
                    st.rerun()
        
        st.markdown("---")
    
    # AI 설정
    st.markdown("### 🤖 AI 설정")
    
    ai_provider = st.selectbox(
        "AI 서비스",
        ["OpenAI (GPT)", "Google Gemini"],
        key="ai_provider"
    )
    
    api_key = st.text_input(
        "API 키",
        type="password",
        placeholder="sk-... 또는 AI...",
        key="api_key"
    )
    
    if api_key:
        save_setting('api_key_hint', api_key[:10] + '...')
    
    tone = st.selectbox(
        "답글 톤",
        ["친절하고 감사한", "전문적이고 격식있는", "친근하고 캐주얼한", "정중하고 사과하는"],
        key="tone_select"
    )
    
    include_emoji = st.checkbox("이모지 포함", value=True, key="emoji_check")
    max_length = st.slider("최대 글자 수", 50, 300, 150, key="max_length")
    
    st.markdown("---")
    
    # 통계
    if st.session_state.reviews:
        st.markdown("### 📊 통계")
        total = len(st.session_state.reviews)
        no_reply = len([r for r in st.session_state.reviews if not r.has_reply])
        has_reply = total - no_reply
        
        col1, col2 = st.columns(2)
        col1.metric("전체", total)
        col2.metric("미답글", no_reply, delta=f"-{has_reply}" if has_reply > 0 else None, delta_color="normal")

# ============ 메인 콘텐츠 ============
st.markdown('<p class="main-header">🏪 네이버 플레이스 리뷰 관리</p>', unsafe_allow_html=True)

if not st.session_state.logged_in:
    # 로그인 전 화면
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 📝 리뷰 관리
        네이버 스마트플레이스 리뷰를 한 곳에서 관리하세요.
        답글 유무를 한눈에 확인할 수 있습니다.
        """)
    
    with col2:
        st.markdown("""
        ### 🤖 AI 답글 생성
        GPT 또는 Gemini를 활용해 
        자연스러운 답글을 자동으로 생성합니다.
        """)
    
    with col3:
        st.markdown("""
        ### ⚡ 빠른 등록
        생성된 답글을 검토 후
        바로 등록할 수 있습니다.
        """)
    
    st.markdown("---")
    
    st.info("👈 **왼쪽 사이드바**에서 네이버 쿠키로 로그인해주세요.")
    
    # 사용 가이드
    with st.expander("📖 상세 사용 가이드"):
        st.markdown("""
        ### 1️⃣ 네이버 쿠키 가져오기
        
        1. **크롬 브라우저**에서 [네이버](https://naver.com)에 로그인합니다.
        2. **F12** 키를 눌러 개발자 도구를 엽니다.
        3. **Application** 탭 → **Cookies** → `https://www.naver.com` 클릭
        4. 아래 쿠키 값들을 찾아 복사합니다:
           - `NID_AUT`
           - `NID_SES`
        5. 형식: `NID_AUT=값; NID_SES=값`
        6. 왼쪽 입력창에 붙여넣기합니다.
        
        ⚠️ **주의**: 쿠키는 민감한 정보입니다. 타인에게 공유하지 마세요.
        
        ---
        
        ### 2️⃣ AI API 키 발급
        
        **OpenAI (GPT)**
        1. [OpenAI Platform](https://platform.openai.com) 접속
        2. 회원가입/로그인
        3. API Keys 메뉴에서 새 키 생성
        4. `sk-`로 시작하는 키 복사
        
        **Google Gemini**
        1. [Google AI Studio](https://makersuite.google.com/app/apikey) 접속
        2. Google 계정으로 로그인
        3. Create API Key 클릭
        4. 생성된 키 복사
        """)

elif not st.session_state.selected_business:
    st.info("👈 왼쪽 사이드바에서 **업체를 선택**해주세요.")

else:
    # 리뷰 관리 화면
    business = st.session_state.selected_business
    
    st.markdown(f"### 📍 {business['name']}")
    if business.get('category'):
        st.caption(f"카테고리: {business['category']}")
    
    st.markdown("---")
    
    # 필터 및 새로고침
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    
    with col1:
        filter_option = st.selectbox(
            "필터",
            ["전체", "답글 미작성", "답글 완료"],
            key="filter_option",
            label_visibility="collapsed"
        )
    
    with col2:
        sort_option = st.selectbox(
            "정렬",
            ["최신순", "별점 높은순", "별점 낮은순"],
            key="sort_option",
            label_visibility="collapsed"
        )
    
    with col3:
        search_query = st.text_input(
            "검색",
            placeholder="🔍 리뷰 내용 검색...",
            key="search_query",
            label_visibility="collapsed"
        )
    
    with col4:
        refresh_btn = st.button("🔄 새로고침", use_container_width=True)
    
    if refresh_btn:
        with st.spinner("리뷰 불러오는 중..."):
            async def load_reviews():
                scraper = ReviewScraper(st.session_state.naver_auth.context)
                filter_map = {
                    "전체": "all",
                    "답글 미작성": "no_reply",
                    "답글 완료": "has_reply"
                }
                reviews = await scraper.get_reviews(
                    business_id=business['id'],
                    filter_type=filter_map[filter_option]
                )
                return reviews
            
            st.session_state.reviews = run_async(load_reviews())
            
            if st.session_state.reviews:
                st.success(f"✅ {len(st.session_state.reviews)}개 리뷰 로드 완료")
            else:
                st.warning("리뷰를 찾을 수 없습니다. 업체 ID를 확인해주세요.")
    
    st.markdown("---")
    
    # 일괄 처리 버튼
    if st.session_state.reviews:
        no_reply_reviews = [r for r in st.session_state.reviews if not r.has_reply]
        
        if no_reply_reviews:
            st.markdown(f"**미답글 리뷰: {len(no_reply_reviews)}개**")
            
            if st.button(f"🤖 미답글 {len(no_reply_reviews)}개 AI 답글 일괄 생성", type="primary"):
                if not api_key:
                    st.error("❌ AI API 키를 입력해주세요.")
                else:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    provider = AIProvider.OPENAI if "OpenAI" in ai_provider else AIProvider.GEMINI
                    generator = AIReplyGenerator(provider, api_key)
                    
                    for i, review in enumerate(no_reply_reviews):
                        status_text.text(f"생성 중... ({i+1}/{len(no_reply_reviews)})")
                        
                        reply = generator.generate_reply(
                            review_content=review.content,
                            store_name=business['name'],
                            rating=review.rating,
                            tone=get_tone_from_string(tone),
                            include_emoji=include_emoji,
                            max_length=max_length
                        )
                        
                        st.session_state.generated_replies[review.id] = reply
                        progress_bar.progress((i + 1) / len(no_reply_reviews))
                    
                    status_text.text("✅ 완료!")
                    st.success(f"✅ {len(no_reply_reviews)}개 답글 생성 완료!")
    
    # 리뷰 목록
    reviews_to_show = st.session_state.reviews
    
    # 검색 필터
    if search_query:
        reviews_to_show = [r for r in reviews_to_show if search_query.lower() in r.content.lower()]
    
    # 정렬
    if sort_option == "별점 높은순":
        reviews_to_show = sorted(reviews_to_show, key=lambda x: x.rating, reverse=True)
    elif sort_option == "별점 낮은순":
        reviews_to_show = sorted(reviews_to_show, key=lambda x: x.rating)
    
    if not reviews_to_show:
        if st.session_state.reviews:
            st.info("검색 결과가 없습니다.")
        else:
            st.info("🔄 **새로고침** 버튼을 눌러 리뷰를 불러오세요.")
    
    for review in reviews_to_show:
        with st.container():
            # 리뷰 헤더
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                st.markdown(f"**{review.author}**")
            with col2:
                st.markdown(f"<span class='rating-stars'>{'⭐' * review.rating}</span>", unsafe_allow_html=True)
            with col3:
                st.caption(review.date)
            
            # 리뷰 내용
            st.markdown(f"> {review.content}")
            
            if review.visit_count:
                st.caption(f"🚶 {review.visit_count}")
            
            # 답글 상태
            if review.has_reply:
                st.markdown('<span class="has-reply-badge">✅ 답글 완료</span>', unsafe_allow_html=True)
                if review.reply_content:
                    with st.expander("💬 사장님 답글 보기"):
                        st.info(review.reply_content)
                        if review.reply_date:
                            st.caption(f"작성일: {review.reply_date}")
            else:
                st.markdown('<span class="no-reply-badge">⏳ 답글 미작성</span>', unsafe_allow_html=True)
                
                # 답글 작성 UI
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    if st.button("🤖 AI 답글 생성", key=f"ai_{review.id}"):
                        if not api_key:
                            st.error("❌ AI API 키를 입력해주세요.")
                        else:
                            with st.spinner("답글 생성 중..."):
                                provider = AIProvider.OPENAI if "OpenAI" in ai_provider else AIProvider.GEMINI
                                generator = AIReplyGenerator(provider, api_key)
                                
                                generated_reply = generator.generate_reply(
                                    review_content=review.content,
                                    store_name=business['name'],
                                    rating=review.rating,
                                    tone=get_tone_from_string(tone),
                                    include_emoji=include_emoji,
                                    max_length=max_length
                                )
                                
                                st.session_state.generated_replies[review.id] = generated_reply
                                st.rerun()
                
                # 답글 입력창
                default_reply = st.session_state.generated_replies.get(review.id, "")
                
                reply_content = st.text_area(
                    "답글 내용",
                    value=default_reply,
                    key=f"textarea_{review.id}",
                    height=100,
                    placeholder="답글을 입력하거나 AI로 생성하세요..."
                )
                
                with col2:
                    if st.button("📤 답글 등록", key=f"post_{review.id}", type="primary"):
                        if not reply_content:
                            st.error("답글 내용을 입력해주세요.")
                        else:
                            with st.spinner("답글 등록 중..."):
                                async def post():
                                    poster = ReplyPoster(st.session_state.naver_auth.context)
                                    result = await poster.post_reply(
                                        business_id=business['id'],
                                        review_id=review.id,
                                        reply_content=reply_content
                                    )
                                    return result
                                
                                result = run_async(post())
                                
                                if result['success']:
                                    st.success(result['message'])
                                    # 히스토리 저장
                                    save_reply_history(
                                        business_id=business['id'],
                                        business_name=business['name'],
                                        review_id=review.id,
                                        review_author=review.author,
                                        review_content=review.content,
                                        review_rating=review.rating,
                                        reply_content=reply_content,
                                        ai_generated=review.id in st.session_state.generated_replies
                                    )
                                else:
                                    st.error(result['message'])
            
            st.markdown("---")

# ============ 푸터 ============
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.85rem;'>
    ⚠️ 본 서비스는 네이버 공식 서비스가 아닙니다. 사용에 따른 책임은 사용자에게 있습니다.<br>
    💡 문의: 개발자에게 연락하세요
</div>
""", unsafe_allow_html=True)
