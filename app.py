import streamlit as st
import requests
import base64
import json
from openai import OpenAI


# ==================================================
# 1. Streamlit 설정
# ==================================================

st.set_page_config(
    page_title="AI 윤리 시험 보호 시스템",
    page_icon="🛡️",
    layout="centered"
)

st.title("🛡️ AI 윤리 시험 보호 시스템")

st.caption(
    "OpenAI Vision과 인터넷 검색을 활용한 "
    "시험 환경 위험 신호 분석 시스템"
)


# ==================================================
# 2. API 키 연결
# ==================================================

try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    TAVILY_API_KEY = st.secrets["TAVILY_API_KEY"]
    ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]

    client = OpenAI(api_key=OPENAI_API_KEY)

except Exception:
    st.error(
        "Secrets 설정을 확인하세요. "
        "OPENAI_API_KEY, TAVILY_API_KEY, "
        "ADMIN_PASSWORD가 필요합니다."
    )
    st.stop()


# ==================================================
# 3. 시험 항목
# ==================================================

exam = [
    "수험표",
    "인터넷에서 확인되지 않은 문제",
    "OMR 카드"
]


# ==================================================
# 4. 세션 초기화
# ==================================================

defaults = {
    "result": None,
    "ai_allowed": None,
    "admin_approved": False,
    "admin_authenticated": False
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ==================================================
# 5. JSON 응답 처리
# ==================================================

def parse_json(text):

    start = text.find("{")
    end = text.rfind("}") + 1

    if start == -1 or end <= start:
        raise ValueError("AI JSON 응답을 읽을 수 없습니다.")

    return json.loads(text[start:end])


# ==================================================
# 6. OpenAI 이미지 분석
# ==================================================

def analyze_image(image):

    encoded_image = base64.b64encode(
        image.getvalue()
    ).decode("utf-8")

    image_url = (
        f"data:{image.type};base64,{encoded_image}"
    )

    prompt = """
    당신은 시험 환경의 시각적 요소를 분석하는 AI입니다.

    이미지에서 다음 요소를 확인하세요.

    1. 수험표(ticket)
    2. OMR 답안지(omr)
    3. 시험 문제 텍스트(question_text)

    반드시 아래 JSON 형식으로 응답하세요.

    {
        "ticket": false,
        "omr": false,
        "question_text": "",
        "confidence": "high",
        "explanation": ""
    }

    판단 기준:

    - 수험표가 명확하게 보일 때만 ticket=true
    - OMR 답안지가 명확하게 보일 때만 omr=true
    - 읽을 수 있는 문제 텍스트를 추출
    - 보이지 않는 항목을 추측하지 말 것
    - 판별이 어려우면 confidence=low
    - 수험표나 OMR이 있다는 사실만으로 부정행위를 확정하지 말 것
    """

    response = client.responses.create(
        model="gpt-4o",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": prompt
                    },
                    {
                        "type": "input_image",
                        "image_url": image_url,
                        "detail": "high"
                    }
                ]
            }
        ]
    )

    result = parse_json(response.output_text)

    if not isinstance(result.get("ticket"), bool):
        raise ValueError("수험표 분석값 오류")

    if not isinstance(result.get("omr"), bool):
        raise ValueError("OMR 분석값 오류")

    if not isinstance(result.get("question_text"), str):
        raise ValueError("문제 텍스트 분석값 오류")

    if result.get("confidence") not in [
        "high", "medium", "low"
    ]:
        raise ValueError("AI 신뢰도 값 오류")

    return result


# ==================================================
# 7. Tavily 인터넷 검색
# ==================================================

def search_question(question):

    if not question or len(question.strip()) < 5:
        return {
            "success": False,
            "found": False,
            "results": [],
            "reason": "검색할 문제 텍스트가 부족합니다."
        }

    url = "https://api.tavily.com/search"

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": question[:500],
        "search_depth": "advanced",
        "max_results": 5
    }

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        results = data.get("results", [])

        if not results:
            return {
                "success": True,
                "found": False,
                "results": [],
                "reason": "검색 결과 없음"
            }

        return {
            "success": True,
            "found": None,
            "results": results,
            "reason": ""
        }

    except requests.RequestException as e:

        return {
            "success": False,
            "found": False,
            "results": [],
            "reason": str(e)
        }


# ==================================================
# 8. 검색 결과와 문제 비교
# ==================================================

def verify_question(question, search_results):

    if not search_results:
        return {
            "success": True,
            "found": False,
            "explanation": "검색 결과가 없습니다."
        }

    evidence = []

    for item in search_results[:5]:
        evidence.append({
            "title": item.get("title", ""),
            "content": item.get("content", "")[:1500],
            "url": item.get("url", "")
        })

    prompt = f"""
    다음 시험 문제와 인터넷 검색 결과를 비교하세요.

    시험 문제:
    {question}

    검색 결과:
    {json.dumps(evidence, ensure_ascii=False)}

    검색 결과가 실제로 동일하거나 실질적으로 동일한 문제인지 판단하세요.

    단순히 같은 과목이나 비슷한 주제라는 이유만으로
    동일한 문제라고 판단하지 마세요.

    아래 JSON 형식으로만 응답하세요.

    {{
        "found": true,
        "explanation": "판단 근거"
    }}
    """

    response = client.responses.create(
        model="gpt-4o",
        input=prompt
    )

    result = parse_json(response.output_text)

    if not isinstance(result.get("found"), bool):
        raise ValueError("검색 비교 결과 오류")

    return {
        "success": True,
        "found": result["found"],
        "explanation": result.get("explanation", "")
    }


# ==================================================
# 9. check_exam 함수
# ==================================================

def check_exam(image):

    # 1. 사진 분석
    vision = analyze_image(image)

    # 2. 문제 검색
    search = search_question(
        vision["question_text"]
    )

    # 3. 검색 결과 비교
    if search["success"] and search["results"]:

        verification = verify_question(
            vision["question_text"],
            search["results"]
        )

        search["found"] = verification["found"]
        search["explanation"] = verification["explanation"]

    elif search["success"]:

        search["found"] = False
        search["explanation"] = "검색 결과가 없습니다."

    else:

        search["explanation"] = search["reason"]

    # 4. data 리스트
    data = [0, 0, 0]

    # 수험표
    if vision["ticket"]:
        data[0] = 2

    # 인터넷에서 확인되지 않은 문제
    if (
        search["success"]
        and search["found"] is False
        and vision["question_text"].strip()
    ):
        data[1] = 1

    # OMR 카드
    if vision["omr"]:
        data[2] = 1

    # 5. 총점
    total = sum(data)

    return {
        "exam": exam,
        "data": data,
        "total": total,
        "vision": vision,
        "search": search
    }


# ==================================================
# 10. AI 접근 허용 판단
# ==================================================

def determine_access(result):

    if result["total"] >= 2:
        return False

    if result["vision"]["confidence"] == "low":
        return False

    if not result["search"]["success"]:
        return False

    if not result["vision"]["question_text"].strip():
        return False

    return True


# ==================================================
# 11. OpenAI 문제풀이
# ==================================================

def solve_question(question):

    response = client.responses.create(
        model="gpt-4o",
        input=[
            {
                "role": "user",
                "content": (
                    "다음 문제를 단계별로 풀이하세요.\n\n"
                    + question
                )
            }
        ]
    )

    return response.output_text


# ==================================================
# 12. 이미지 업로드
# ==================================================

st.header("📷 시험 이미지 업로드")

uploaded_image = st.file_uploader(
    "사진을 업로드하세요.",
    type=["jpg", "jpeg", "png", "webp"]
)

if uploaded_image:

    st.image(
        uploaded_image,
        caption="업로드한 이미지",
        use_container_width=True
    )

    if st.button(
        "🔍 OpenAI AI 자동 분석",
        type="primary"
    ):

        st.session_state.result = None
        st.session_state.ai_allowed = None
        st.session_state.admin_approved = False
        st.session_state.admin_authenticated = False

        with st.spinner(
            "OpenAI Vision 이미지 분석 및 인터넷 검색 중..."
        ):

            try:

                result = check_exam(uploaded_image)

                st.session_state.result = result

                st.session_state.ai_allowed = (
                    determine_access(result)
                )

                st.success("AI 분석 완료!")

            except Exception as e:

                st.session_state.result = None
                st.session_state.ai_allowed = None

                st.error(
                    f"분석 오류: {str(e)}"
                )


# ==================================================
# 13. 분석 결과
# ==================================================

if st.session_state.result is not None:

    result = st.session_state.result

    st.divider()

    st.header("📊 AI 분석 결과")

    for i, item in enumerate(result["exam"]):

        st.write(
            f"**{item}** : {result['data'][i]}점"
        )

    st.metric(
        "위험 신호 점수",
        f"{result['total']}점"
    )

    st.subheader("이미지 분석 설명")

    st.write(
        result["vision"]["explanation"]
    )

    st.write(
        "AI 신뢰도:",
        result["vision"]["confidence"]
    )

    st.subheader("추출된 문제")

    st.write(
        result["vision"]["question_text"]
        or "문제 텍스트 없음"
    )

    st.subheader("인터넷 검색 결과")

    search = result["search"]

    if not search["success"]:

        st.error(
            "검색 실패: " + search["reason"]
        )

    elif search["found"]:

        st.success("동일하거나 실질적으로 동일한 문제를 발견했습니다.")

    else:

        st.warning(
            "동일한 문제를 확인하지 못했습니다. "
            "검색되지 않았다는 사실만으로 부정행위를 의미하지 않습니다."
        )

    st.write(search.get("explanation", ""))

    for item in search.get("results", []):

        if item.get("url"):

            st.markdown(
                f"- [{item.get('title', '검색 결과')}]"
                f"({item['url']})"
            )

    st.divider()

    # ==================================================
    # 14. AI 접근 제어
    # ==================================================

    st.header("🔐 문제풀이 접근 제어")

    if st.session_state.ai_allowed:

        st.success(
            "위험 신호 기준 이하: 문제풀이 기능 사용 가능"
        )

    else:

        st.error(
            "문제풀이 기능이 일시적으로 보류되었습니다."
        )

        st.info(
            "자동 판정은 부정행위 확정이 아닙니다. "
            "관리자의 확인이 필요합니다."
        )

    # ==================================================
    # 15. 관리자 승인
    # ==================================================

    if not st.session_state.ai_allowed:

        st.subheader("👨‍💼 관리자 검토")

        with st.form("admin_form"):

            password = st.text_input(
                "관리자 비밀번호",
                type="password"
            )

            approve = st.form_submit_button(
                "관리자 승인"
            )

        if approve:

            if password == ADMIN_PASSWORD:

                st.session_state.admin_authenticated = True

                st.success("관리자 인증 완료")

                st.warning(
                    "검사 결과를 검토한 후 아래 버튼으로 승인하세요."
                )

            else:

                st.error("비밀번호가 올바르지 않습니다.")

        if st.session_state.admin_authenticated:

            if st.button("검토 완료 및 문제풀이 허용"):

                st.session_state.admin_approved = True
                st.session_state.ai_allowed = True

                st.success(
                    "관리자 승인 완료. 문제풀이 기능이 허용되었습니다."
                )


# ==================================================
# 16. 문제풀이 화면
# ==================================================

st.divider()

st.header("🤖 OpenAI 문제풀이")

if st.session_state.ai_allowed is True:

    st.success("문제풀이 API 사용 가능")

    question = st.text_area(
        "문제를 입력하세요.",
        height=150
    )

    if st.button("문제 풀이 시작"):

        if question.strip():

            with st.spinner("OpenAI가 문제를 풀이하고 있습니다..."):

                try:

                    answer = solve_question(question)

                    st.subheader("AI 풀이 결과")

                    st.write(answer)

                except Exception as e:

                    st.error(
                        f"문제풀이 오류: {str(e)}"
                    )

        else:

            st.warning("문제를 입력하세요.")

elif st.session_state.ai_allowed is False:

    st.error(
        "현재 문제풀이 기능이 보류되었습니다."
    )

else:

    st.info(
        "사진 분석을 먼저 진행하세요."
    )


# ==================================================
# 17. 초기화
# ==================================================

st.divider()

if st.button("🔄 새로운 검사 시작"):

    st.session_state.result = None
    st.session_state.ai_allowed = None
    st.session_state.admin_approved = False
    st.session_state.admin_authenticated = False

    st.rerun()


# ==================================================
# 18. 하단 안내
# ==================================================

st.caption(
    "AI 윤리 시험 보호 시스템 | "
    "자동 분석은 참고 자료이며 최종 판단은 관리자가 수행합니다."
)
