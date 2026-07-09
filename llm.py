import json
import anthropic
import streamlit as st

_MODEL_NAME = "claude-opus-4-8"


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])


def analyze_dream(dream_content: str, dream_type: str) -> dict:
    """
    꿈 내용을 분석해 해석 텍스트, 회상 점수, 반복 요소를 반환.

    Returns:
        {
            "analysis_text": str,
            "recall_score": int,          # 0~10
            "recurring_people": list[str],
            "recurring_places": list[str],
            "recurring_emotions": list[str],
        }
    """
    prompt = f"""당신은 꿈 분석 전문가입니다. 아래 꿈일기를 읽고 JSON 형식으로만 응답하세요.

꿈 타입: {dream_type}
꿈 내용:
{dream_content}

---
## 채점 기준 (recall_score 0~10점)
- 10점: 시각·청각·촉각·냄새 등 다감각, 대화 내용, 인물 세부 묘사, 시간 흐름, 감정까지 풍부하게 기억
- 7~9점: 주요 사건 흐름 + 2개 이상 감각 + 인물·장소 구체적
- 4~6점: 전반적 줄거리는 있으나 세부 묘사·감각이 부족
- 2~3점: 단편적 장면만 기억, 줄거리 불명확
- 1점: 꿈을 꿨다는 사실 외 거의 기억 없음
- 0점: NO_MEMORY 타입일 때만 사용

## 응답 형식 (JSON만, 코드블록 없이)
{{
  "analysis_text": "꿈 해석 및 상징 분석 (3~5문장, 한국어, 추측은 '~같다/~일 수 있다' 표현 사용)",
  "recall_score": <정수 0~10>,
  "recurring_people": ["인물1", "인물2"],
  "recurring_places": ["장소1"],
  "recurring_emotions": ["감정1", "감정2"]
}}"""

    try:
        response = _client().messages.create(
            model=_MODEL_NAME,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        return {
            "analysis_text": f"분석 중 오류 발생: {e}",
            "recall_score": None,
            "recurring_people": [],
            "recurring_places": [],
            "recurring_emotions": [],
        }


def get_partial_recall_prompt(dream_content: str) -> list:
    """'기억 안 남' 상태일 때 회상 유도 질문을 생성."""
    prompt = f"""꿈일기: {dream_content if dream_content else '(내용 없음)'}

위 내용을 바탕으로, 사용자가 꿈을 더 떠올릴 수 있도록 도와주는 유도 질문 3가지를 짧고 구체적으로 만들어 주세요.
JSON 배열로만 응답하세요 (코드블록 없이): ["질문1", "질문2", "질문3"]"""

    try:
        response = _client().messages.create(
            model=_MODEL_NAME,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception:
        return [
            "마지막으로 떠오르는 장면이나 색이 있나요?",
            "잠에서 깰 때 어떤 감정이 남아 있었나요?",
            "누군가와 함께 있었나요, 아니면 혼자였나요?",
        ]


def generate_mild_intention(dream_signs: list) -> str:
    """드림사인 목록으로 오늘 밤 MILD 인텐션 문장을 생성."""
    signs_str = ", ".join(dream_signs) if dream_signs else "아직 파악된 드림사인 없음"
    prompt = f"""드림사인: {signs_str}

위 드림사인을 활용해 자기 전 되뇔 MILD 인텐션 문장을 한 문장으로 만들어 주세요.
형식: "오늘 밤 꿈에서 [드림사인]이 나오면, 나는 지금 꿈을 꾸고 있다는 것을 알아차리겠다."
문장만 출력하세요."""

    try:
        response = _client().messages.create(
            model=_MODEL_NAME,
            max_tokens=128,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"MILD 인텐션 생성 실패: {e}"


def summarize_week(dreams: list) -> str:
    """주간 꿈 목록으로 요약 리포트를 생성."""
    if not dreams:
        return "이번 주 기록된 꿈이 없습니다."

    entries = "\n\n".join(
        f"[{d['dream_date']}] {d['title']}\n{d['content'][:300]}" for d in dreams
    )
    prompt = f"""아래는 이번 주 꿈일기입니다.

{entries}

이 꿈들의 공통 패턴, 반복 요소, 감정 변화를 3~5문장으로 요약해 주세요. 한국어로 작성하세요."""

    try:
        response = _client().messages.create(
            model=_MODEL_NAME,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"요약 생성 실패: {e}"


def cluster_dream_signs(elements: list) -> dict:
    """반복 요소를 의미상 그룹핑해 드림사인 Top 5 반환."""
    from collections import Counter
    freq = dict(Counter(elements).most_common(60))

    prompt = f"""아래는 꿈일기에서 반복적으로 나타난 인물/장소/감정 요소와 등장 횟수야.
의미상 유사한 것끼리 묶어서 나만의 드림사인 Top 5를 찾아줘. 한국어로 작성해.

빈도 목록:
{json.dumps(freq, ensure_ascii=False)}

JSON 형식으로만 응답해 (코드블록 없이):
{{
  "dream_signs": [
    {{"sign": "드림사인 이름", "description": "한 줄 설명", "elements": ["관련 요소1", "요소2"], "count": 총합산숫자}},
    ...
  ]
}}"""

    try:
        response = _client().messages.create(
            model=_MODEL_NAME,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        return {"dream_signs": [], "error": str(e)}


def search_by_meaning(query: str, dreams: list) -> list:
    """자연어 쿼리와 의미상 관련된 꿈 ID 목록 반환."""
    if not dreams:
        return []

    entries = "\n".join(
        f"ID:{d['id']} [{d['dream_date']}] {(d.get('title') or '').strip() or '제목없음'}: {d['content'][:150]}"
        for d in dreams
    )

    prompt = f"""아래 꿈일기 목록에서 검색어와 의미상 관련된 꿈을 찾아줘.

검색어: {query}

꿈 목록:
{entries}

관련 있는 꿈의 ID만 JSON 배열로 응답해 (코드블록 없이): [1, 5, 12]
관련 꿈이 없으면: []"""

    try:
        response = _client().messages.create(
            model=_MODEL_NAME,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception:
        return []
