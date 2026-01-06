import openai
from typing import Optional
from enum import Enum

class AIProvider(Enum):
    OPENAI = "openai"
    GEMINI = "gemini"

class ReplyTone(Enum):
    FRIENDLY = "friendly"           # 친절하고 감사한
    PROFESSIONAL = "professional"   # 전문적이고 격식있는
    CASUAL = "casual"               # 친근하고 캐주얼한
    APOLOGETIC = "apologetic"       # 정중하고 사과하는

class AIReplyGenerator:
    def __init__(self, provider: AIProvider, api_key: str):
        """
        Args:
            provider: AI 서비스 제공자 (openai/gemini)
            api_key: API 키
        """
        self.provider = provider
        self.api_key = api_key
        self.gemini_model = None
        
        if provider == AIProvider.OPENAI:
            openai.api_key = api_key
        elif provider == AIProvider.GEMINI:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self.gemini_model = genai.GenerativeModel('gemini-pro')
            except ImportError:
                print("google-generativeai 패키지가 설치되지 않았습니다.")
    
    def generate_reply(
        self,
        review_content: str,
        store_name: str,
        rating: int,
        tone: ReplyTone = ReplyTone.FRIENDLY,
        custom_instruction: Optional[str] = None,
        include_emoji: bool = True,
        max_length: int = 150
    ) -> str:
        """
        리뷰에 대한 AI 답글 생성
        """
        prompt = self._build_prompt(
            review_content=review_content,
            store_name=store_name,
            rating=rating,
            tone=tone,
            custom_instruction=custom_instruction,
            include_emoji=include_emoji,
            max_length=max_length
        )
        
        if self.provider == AIProvider.OPENAI:
            return self._generate_openai(prompt)
        else:
            return self._generate_gemini(prompt)
    
    def _build_prompt(
        self,
        review_content: str,
        store_name: str,
        rating: int,
        tone: ReplyTone,
        custom_instruction: Optional[str],
        include_emoji: bool,
        max_length: int
    ) -> str:
        """프롬프트 생성"""
        
        tone_descriptions = {
            ReplyTone.FRIENDLY: "친절하고 따뜻하며 감사함을 표현하는",
            ReplyTone.PROFESSIONAL: "전문적이고 격식있으며 신뢰감을 주는",
            ReplyTone.CASUAL: "친근하고 캐주얼하며 편안한",
            ReplyTone.APOLOGETIC: "진심으로 사과하고 개선을 약속하는"
        }
        
        # 별점에 따른 추가 지시
        if rating <= 2:
            rating_instruction = """
- 불편을 드린 점에 대해 진심으로 사과해주세요
- 구체적인 개선 의지를 보여주세요
- 재방문 시 더 나은 서비스를 약속해주세요"""
        elif rating == 3:
            rating_instruction = """
- 방문에 감사드리며 아쉬운 점에 대해 개선하겠다고 말씀해주세요
- 다음 방문 시 더 만족하실 수 있도록 노력하겠다고 해주세요"""
        else:
            rating_instruction = """
- 좋은 평가에 진심으로 감사드린다고 해주세요
- 리뷰 내용 중 구체적인 부분을 언급해주세요
- 재방문을 부탁드린다고 해주세요"""
        
        emoji_instruction = "- 이모지를 1~2개 자연스럽게 사용해주세요" if include_emoji else "- 이모지는 사용하지 마세요"
        
        custom = f"\n추가 요청사항: {custom_instruction}" if custom_instruction else ""
        
        prompt = f"""당신은 '{store_name}'의 사장님입니다.
고객이 남긴 리뷰에 {tone_descriptions[tone]} 톤으로 답글을 작성해주세요.

## 작성 규칙
- {max_length}자 이내로 작성해주세요
- 자연스럽고 진정성 있게 작성해주세요
- 기계적이거나 복붙한 느낌이 들지 않게 해주세요
- 한국어로 작성해주세요
{rating_instruction}
{emoji_instruction}
{custom}

## 고객 리뷰 (별점: {'⭐' * rating})
"{review_content}"

## 사장님 답글:"""

        return prompt
    
    def _generate_openai(self, prompt: str) -> str:
        """OpenAI GPT로 답글 생성"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 자영업자의 리뷰 답글 작성을 도와주는 어시스턴트입니다. 자연스럽고 진정성 있는 한국어 답글을 작성해주세요."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=300,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"답글 생성 오류: {str(e)}"
    
    def _generate_gemini(self, prompt: str) -> str:
        """Google Gemini로 답글 생성"""
        try:
            if not self.gemini_model:
                return "Gemini 모델이 초기화되지 않았습니다."
            
            response = self.gemini_model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"답글 생성 오류: {str(e)}"
    
    def generate_bulk_replies(
        self,
        reviews: list,
        store_name: str,
        tone: ReplyTone = ReplyTone.FRIENDLY,
        **kwargs
    ) -> list:
        """
        여러 리뷰에 대한 답글 일괄 생성
        """
        results = []
        for review in reviews:
            reply = self.generate_reply(
                review_content=review.get('content', ''),
                store_name=store_name,
                rating=review.get('rating', 5),
                tone=tone,
                **kwargs
            )
            results.append({
                'review_id': review.get('id'),
                'reply': reply
            })
        return results


def get_tone_from_string(tone_str: str) -> ReplyTone:
    """문자열에서 ReplyTone enum 반환"""
    tone_map = {
        "친절하고 감사한": ReplyTone.FRIENDLY,
        "전문적이고 격식있는": ReplyTone.PROFESSIONAL,
        "친근하고 캐주얼한": ReplyTone.CASUAL,
        "정중하고 사과하는": ReplyTone.APOLOGETIC
    }
    return tone_map.get(tone_str, ReplyTone.FRIENDLY)
