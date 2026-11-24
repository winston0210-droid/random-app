import streamlit as st
from google import genai
import time
from PIL import Image

st.set_page_config(page_title="AI 윤리 - 부정행위 방지 안경", page_icon="👓")
st.title("👓 AI 안경 부정행위 감지 시스템 (Google Gemini)")
st.write("Gemini 비전 AI가 스마트 안경에 포착된 시야를 직접 분석하여 부정행위 여부를 판별하고 문제를 풀이합니다.")

# Secrets에 저장된 API 키를 자동으로 불러오기
if "GOOGLE_API_KEY" in st.secrets:
    google_api_key = st.secrets["GOOGLE_API_KEY"]
else:
    st.error("⚠️ Streamlit Cloud 설정(Secrets)에 GOOGLE_API_KEY가 등록되지 않았습니다.")
    st.stop()

# 1. Gemini 비전 AI가 사진을 보고 수험표/새로운 문제/OMR 카드를 판별하는 함수
def analyze_image_with_gemini(client, img):
    prompt = """
    이 사진은 스마트 안경으로 촬영된 이미지입니다. 
    사진 속에 다음 3가지 요소가 있는지 확인해주세요.
    1. '수험표' (시험 응시자의 이름, 수험번호 등이 적힌 표)
    2. 'OMR카드' (컴퓨터용 사인펜으로 마킹하는 객관식 답안지)
    3. '새로운_문제' (일반적인 문제집이나 교과서가 아니라 실제 시험지 양식의 문제인지 여부)
    
    사진에 포함되어 있다고 판단되는 단어만 쉼표(,)로 구분해서 정확히 출력하세요.
    예시 출력: 수험표, OMR카드
    해당하는 것이 하나도 없으면 '없음'이라고만 출력하세요. 다른 설명은 절대 쓰지 마세요.
    """
    
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=[prompt, img]
    )
    
    result_text = response.text.strip()
    st.write(f"**AI 1차 시각 분석 결과:** `{result_text}`")
    return [item.strip() for item in result_text.split(',')]

# 2. 통과 시 어떤 과목/유형의 문제든 Gemini가 직접 풀어주는 함수
def solve_problem_with_gemini(client, img):
    prompt = "이 사진에 있는 문제를 정확히 읽고, 어떤 과목인지 파악한 뒤 학생이 이해하기 쉽게 단계별 풀이 과정과 최종 정답을 한국어로 알려줘."
    
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=[prompt, img]
    )
    return response.text

# 3. 핵심 검사 함수: exam_check(exam, total)
def exam_check(exam, total):
    data = [0, 0, 0]
    
    if '수험표' in exam:
        data[0] = 2
        st.warning("🚨 [감지] 수험표가 확인되었습니다. (+2점)")
        
    if '새로운_문제' in exam:
        data[1] = 1
        st.warning("🚨 [감지] 시험지 양식(새로운 문제)이 확인되었습니다. (+1점)")
        
    if 'OMR카드' in exam:
        data[2] = 1
        st.warning("🚨 [감지] OMR 카드가 확인되었습니다. (+1점)")
        
    total = sum(data)
    st.subheader(f"📊 최종 합산 위험도 점수: {total}점")
    
    if total >= 2:
        st.error("⛔ 부정행위 위험 기준(2점 이상)을 초과하여 외부 AI 접속을 영구 차단합니다.")
        while True:
            st.error("AI 판단결과 부정행위 우려가 있으므로 문제풀이를 거부합니다")
            time.sleep(1.5)
    else:
        st.success("✅ 부정행위 우려가 없습니다. 외부 AI 문제 풀이를 허용합니다.")
        return True

# 메인 화면 UI
tab1, tab2 = st.tabs(["📁 사진 파일 업로드", "📷 웹캠 직접 촬영"])
uploaded_image = None

with tab1:
    file = st.file_uploader("테스트할 문제, 시험지, 수험표 사진을 올려주세요", type=["jpg", "jpeg", "png"])
    if file is not None:
        uploaded_image = Image.open(file).convert("RGB")

with tab2:
    cam_file = st.camera_input("카메라로 사물을 비추고 촬영 버튼을 누르세요")
    if cam_file is not None:
        uploaded_image = Image.open(cam_file).convert("RGB")

if uploaded_image is not None:
    st.image(uploaded_image, caption="안경에 포착된 화면", use_container_width=True)
    
    if st.button("🔍 AI 윤리 검사 및 문제 풀이 실행", type="primary"):
        client = genai.Client(api_key=google_api_key)
        
        with st.spinner("Gemini 비전 AI가 사진 속 사물과 상황을 분석하는 중입니다..."):
            exam = analyze_image_with_gemini(client, uploaded_image)
            total = 0
            is_safe = exam_check(exam, total)
            
            if is_safe:
                with st.spinner("Gemini가 문제를 읽고 풀이를 작성하는 중입니다..."):
                    solution = solve_problem_with_gemini(client, uploaded_image)
                    st.markdown("### 📝 AI 문제 풀이 결과")
                    st.write(solution)
