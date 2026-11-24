import streamlit as st
import time
from google import genai
from PIL import Image

# 페이지 기본 설정
st.set_page_config(page_title="AI 윤리 - 부정행위 방지 안경", page_icon="👓")

st.title("👓 AI 안경 부정행위 감지 시스템")
st.write("스마트 안경으로 촬영된 시야(사진)를 분석하여 부정행위 여부를 판별합니다.")

# 사이드바에서 API 키 입력받기 (보안상 코드에 직접 적지 않고 화면에서 입력)
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    api_key = st.text_input("Gemini API 키를 입력하세요", type="password")
    st.info("API 키가 없으면 이미지 분석 및 문제 풀이가 작동하지 않습니다.")

# 제미나이 이미지 분석 함수
def analyze_image_with_gemini(client, img):
    prompt = """
    이 사진은 스마트 안경으로 촬영된 이미지입니다. 
    사진 속에 다음 3가지 요소가 있는지 엄격하게 확인해주세요.
    1. '수험표' (시험 응시자의 이름, 수험번호 등이 적힌 표)
    2. 'OMR카드' (컴퓨터용 사인펜으로 마킹하는 객관식 답안지)
    3. '새로운_문제' (일반적인 기출문제가 아니라 시험지 형태의 시험 문제인지 여부)
    
    판단 결과, 사진에 포함되어 있다고 판단되는 단어만 쉼표(,)로 구분해서 정확히 출력하세요.
    예시 출력: 수험표, OMR카드
    해당하는 것이 하나도 없으면 '없음'이라고만 출력하세요.
    """
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[img, prompt]
    )
    result_text = response.text.strip()
    return [item.strip() for item in result_text.split(',')]

# 문제 풀이 함수
def solve_problem_with_gemini(client, img):
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[img, "이 사진에 있는 문제를 파악하고, 학생이 이해하기 쉽게 풀이 과정과 정답을 알려줘."]
    )
    return response.text

# 요청하신 핵심 검사 함수: exam_check(exam, total)
def exam_check(exam, total):
    data = [0, 0, 0]
    
    if '수험표' in exam:
        data[0] = 2
        st.warning("🚨 [감지] 수험표가 확인되었습니다. (+2점)")
        
    if '새로운_문제' in exam:
        data[1] = 1
        st.warning("🚨 [감지] 인터넷에 없는 새로운 시험 문제가 확인되었습니다. (+1점)")
        
    if 'OMR카드' in exam:
        data[2] = 1
        st.warning("🚨 [감지] OMR 카드가 확인되었습니다. (+1점)")
        
    total = sum(data)
    st.subheader(f"📊 최종 합산 위험도 점수: {total}점")
    
    # 총합이 2 이상일 경우: 무한 반복 차단
    if total >= 2:
        st.error("⛔ 부정행위 위험 기준(2점 이상)을 초과하여 외부 AI 접속을 영구 차단합니다.")
        # 스트림릿 화면에서 무한 반복으로 경고 문구 출력
        while True:
            st.error("AI 판단결과 부정행위 우려가 있으므로 문제풀이를 거부합니다")
            time.sleep(1.5) # 1.5초마다 아래로 경고 메시지가 계속 쌓임
            
    # 총합이 1 이하일 경우: 통과
    else:
        st.success("✅ 부정행위 우려가 없습니다. 외부 AI 문제 풀이를 허용합니다.")
        return True

# ==========================================
# 메인 화면 UI (사진 업로드 또는 웹캠 촬영)
# ==========================================
tab1, tab2 = st.tabs(["📁 사진 파일 업로드", "📷 안경 카메라(웹캠) 직접 촬영"])

uploaded_image = None

with tab1:
    file = st.file_uploader("테스트할 시험지/수험표 사진을 올려주세요", type=["jpg", "jpeg", "png"])
    if file is not None:
        uploaded_image = Image.open(file)

with tab2:
    cam_file = st.camera_input("카메라로 사물을 비추고 촬영 버튼을 누르세요")
    if cam_file is not None:
        uploaded_image = Image.open(cam_file)

# 사진이 입력되면 분석 시작
if uploaded_image is not None:
    st.image(uploaded_image, caption="안경에 포착된 화면", use_container_width=True)
    
    if st.button("🔍 AI 윤리 검사 및 문제 풀이 실행", type="primary"):
        if not api_key:
            st.error("왼쪽 사이드바에 Gemini API 키를 먼저 입력해주세요!")
        else:
            client = genai.Client(api_key=api_key)
            
            with st.spinner("AI가 시야 속 사물을 분석하는 중입니다..."):
                # 1. 제미나이가 사진을 분석해 exam 리스트 생성
                exam = analyze_image_with_gemini(client, uploaded_image)
                st.write(f"**AI 탐지 결과 리스트 (`exam`):** `{exam}`")
                
                # 2. exam_check(exam, total) 실행
                total = 0
                is_safe = exam_check(exam, total)
                
                # 3. 안전할 경우에만 문제 풀이 실행
                if is_safe:
                    with st.spinner("제미나이 AI가 문제를 풀고 있습니다..."):
                        solution = solve_problem_with_gemini(client, uploaded_image)
                        st.markdown("### 📝 AI 문제 풀이 결과")
                        st.write(solution)
