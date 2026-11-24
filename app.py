import streamlit as st
from huggingface_hub import InferenceClient
import base64
import io
import time
from PIL import Image

st.set_page_config(page_title="AI 윤리 - 부정행위 방지 안경", page_icon="👓")
st.title("👓 AI 안경 부정행위 감지 시스템")
st.write("실제 비전 AI가 스마트 안경에 포착된 시야를 분석하여 부정행위 여부를 판별하고 문제를 풀이합니다.")

# 사이드바에서 Hugging Face 토큰 입력받기
with st.sidebar:
    st.header("⚙️ AI 연결 설정")
    hf_token = st.text_input("Hugging Face 토큰(hf_...)을 입력하세요", type="password")
    st.caption("Hugging Face 무료 가입 후 Settings > Access Tokens에서 발급받을 수 있습니다.")

# 이미지를 AI에게 전송할 수 있는 형태로 변환
def encode_image(img):
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

# 1. 실제 비전 AI가 사진을 보고 수험표/새로운 문제/OMR 카드를 판별하는 함수
def analyze_image_with_ai(client, base64_img):
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
    
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
            ]
        }
    ]
    
    response = client.chat_completion(
        model="Qwen/Qwen2.5-VL-7B-Instruct",
        messages=messages,
        max_tokens=100
    )
    
    result_text = response.choices[0].message.content.strip()
    st.write(f"**AI 1차 시각 분석 결과:** `{result_text}`")
    return [item.strip() for item in result_text.split(',')]

# 2. 통과 시 어떤 과목/유형의 문제든 실제 AI가 풀어주는 함수
def solve_problem_with_ai(client, base64_img):
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "이 사진에 있는 문제를 정확히 읽고, 어떤 과목인지 파악한 뒤 학생이 이해하기 쉽게 단계별 풀이 과정과 최종 정답을 알려줘."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
            ]
        }
    ]
    
    response = client.chat_completion(
        model="Qwen/Qwen2.5-VL-7B-Instruct",
        messages=messages,
        max_tokens=800
    )
    return response.choices[0].message.content

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
        if not hf_token:
            st.error("왼쪽 사이드바에 Hugging Face 토큰을 먼저 입력해주세요!")
        else:
            client = InferenceClient(api_key=hf_token)
            base64_img = encode_image(uploaded_image)
            
            with st.spinner("실제 비전 AI가 사진 속 사물과 상황을 분석하는 중입니다..."):
                exam = analyze_image_with_ai(client, base64_img)
                total = 0
                is_safe = exam_check(exam, total)
                
                if is_safe:
                    with st.spinner("AI가 문제를 읽고 풀이를 작성하는 중입니다..."):
                        solution = solve_problem_with_ai(client, base64_img)
                        st.markdown("### 📝 AI 문제 풀이 결과")
                        st.write(solution)
