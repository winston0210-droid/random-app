import subprocess
import sys

# ==========================================
# 0단계: 필요한 라이브러리 및 AI 모델 자동 설치 (cmd 입력 불필요)
# ==========================================
def auto_setup():
    # 1. 파이썬 필수 패키지 자동 설치
    packages = ["streamlit", "ollama", "pillow"]
    for pkg in packages:
        try:
            __import__(pkg if pkg != "pillow" else "PIL")
        except ImportError:
            print(f"[자동 설정] {pkg} 라이브러리를 설치하는 중입니다...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

    # 2. Ollama 비전 AI 모델 자동 다운로드 확인
    import ollama
    model_name = "qwen2.5vl:3b"
    try:
        # 현재 설치된 모델 목록 확인
        installed_models = [m['model'] for m in ollama.list().get('models', [])]
        if not any(model_name in m for m in installed_models):
            print(f"[자동 설정] AI 모델({model_name})을 자동으로 다운로드합니다. 잠시만 기다려주세요...")
            ollama.pull(model_name)
            print("[자동 설정] AI 모델 다운로드 완료!")
    except Exception as e:
        print("⚠️ Ollama 프로그램이 아직 실행되지 않았거나 설치되지 않았습니다.")
        print("👉 https://ollama.com 에서 Ollama를 먼저 설치하고 실행해 주세요.")

# 앱 시작 전 자동 설정 실행
auto_setup()

# ==========================================
# 메인 스트림릿 앱 시작
# ==========================================
import streamlit as st
import ollama
import time
import io
from PIL import Image

st.set_page_config(page_title="AI 윤리 - 부정행위 방지 안경", page_icon="👓")
st.title("👓 AI 안경 부정행위 감지 시스템")
st.write("API 키나 복잡한 명령어 없이 로컬 비전 AI가 사진 속 상황과 모든 문제를 직접 분석합니다.")

def image_to_bytes(img):
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    return img_byte_arr.getvalue()

# 1. 비전 AI 이미지 분석 함수
def analyze_image_with_local_ai(img):
    img_bytes = image_to_bytes(img)
    
    prompt = """
    이 사진은 스마트 안경으로 촬영된 이미지입니다. 
    사진 속에 다음 3가지 요소가 있는지 확인해주세요.
    1. '수험표' (시험 응시자의 이름, 수험번호 등이 적힌 표)
    2. 'OMR카드' (컴퓨터용 사인펜으로 마킹하는 객관식 답안지)
    3. '새로운_문제' (일반적인 문제집이나 교과서가 아니라 실제 시험지 양식의 문제인지 여부)
    
    사진에 포함되어 있다고 판단되는 단어만 쉼표(,)로 구분해서 정확히 출력하세요.
    예시 출력: 수험표, OMR카드
    해당하는 것이 하나도 없으면 '없음'이라고만 출력하세요. 다른 설명은 쓰지 마세요.
    """
    
    response = ollama.chat(
        model='qwen2.5vl:3b',
        messages=[{
            'role': 'user',
            'content': prompt,
            'images': [img_bytes]
        }]
    )
    
    result_text = response['message']['content'].strip()
    st.write(f"**AI 1차 시각 분석 결과:** `{result_text}`")
    return [item.strip() for item in result_text.split(',')]

# 2. 모든 과목/유형 문제 풀이 함수
def solve_any_problem_with_local_ai(img):
    img_bytes = image_to_bytes(img)
    
    response = ollama.chat(
        model='qwen2.5vl:3b',
        messages=[{
            'role': 'user',
            'content': '이 사진에 있는 문제를 정확히 읽고, 어떤 과목인지 파악한 뒤 학생이 이해하기 쉽게 단계별 풀이 과정과 최종 정답을 알려줘.',
            'images': [img_bytes]
        }]
    )
    return response['message']['content']

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
    
    # 총합이 2 이상일 경우: 무한 반복 차단
    if total >= 2:
        st.error("⛔ 부정행위 위험 기준(2점 이상)을 초과하여 AI 접속을 영구 차단합니다.")
        while True:
            st.error("AI 판단결과 부정행위 우려가 있으므로 문제풀이를 거부합니다")
            time.sleep(1.5)
            
    # 총합이 1 이하일 경우: 문제 풀이 허용
    else:
        st.success("✅ 부정행위 우려가 없습니다. AI 문제 풀이를 허용합니다.")
        return True

# ==========================================
# 화면 UI
# ==========================================
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
        with st.spinner("로컬 비전 AI가 사진 속 사물과 문제를 분석하는 중입니다..."):
            exam = analyze_image_with_local_ai(uploaded_image)
            total = 0
            is_safe = exam_check(exam, total)
            
            if is_safe:
                with st.spinner("AI가 문제를 읽고 풀이를 작성하는 중입니다..."):
                    solution = solve_any_problem_with_local_ai(uploaded_image)
                    st.markdown("### 📝 AI 문제 풀이 결과")
                    st.write(solution)

# 만약 파이썬 기본 실행 버튼(▶)으로 직접 실행했을 때 자동으로 스트림릿 웹을 띄워주는 코드
if __name__ == "__main__":
    import os
    if not os.environ.get("STREAMLIT_RUN_MAIN"):
        os.environ["STREAMLIT_RUN_MAIN"] = "true"
        subprocess.run([sys.executable, "-m", "streamlit", "run", __file__])
