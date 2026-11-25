import streamlit as st
from google import genai
from google.genai import errors
import time
from PIL import Image
import random

# 발표용 페이지 설정
st.set_page_config(page_title="AI 윤리 - 부정행위 감지 안경", page_icon="👓", layout="centered")
st.title("👓 AI 안경 부정행위 감지 시스템 (발표 전용)")
st.write("실제 비전 AI가 스마트 안경에 포착된 시야를 분석하여 부정행위 여부를 판별하고 문제를 풀이합니다.")

# Secrets에 저장된 API 키를 자동으로 불러오기
if "GOOGLE_API_KEY" in st.secrets:
    google_api_key = st.secrets["GOOGLE_API_KEY"]
else:
    st.error("⚠️ Streamlit Cloud 설정(Secrets)에 GOOGLE_API_KEY가 등록되지 않았습니다.")
    st.stop()

# 1. [핵심] 서버 과부하(503)를 우회하기 위한 4단계 전략 함수
# 1) 트래픽이 적은 'lite' 모델 사용
# 2) 최대 10번 자동 재시도
# 3) 재시도 시 대기 시간 점진적 증가 (1.5초, 3초, 4.5초...)
# 4) 대기 시간에 랜덤성(jitter) 추가 (구글 차단 우회)
def process_image_with_final_retry(client, img):
    prompt = """
    이 사진은 스마트 안경으로 촬영된 이미지입니다. 다음 두 가지 임무를 순서대로 수행하세요.

    [임무 1] 사진 속에 다음 3가지 요소가 있는지 확인하세요.
    1. '수험표' (시험 응시자의 이름, 수험번호 등이 적힌 표)
    2. 'OMR카드' (컴퓨터용 사인펜으로 마킹하는 객관식 답안지)
    3. '새로운_문제' (일반적인 문제집이나 교과서가 아니라 실제 시험지 양식의 문제인지 여부)
    
    첫 번째 줄에는 사진에 포함된 단어만 쉼표(,)로 구분해서 정확히 출력하세요. (없으면 '없음'이라고만 출력)
    예시 첫 줄: 수험표, OMR카드

    [임무 2] 두 번째 줄부터는 사진에 있는 문제를 정확히 읽고, 어떤 과목인지 파악한 뒤 학생이 이해하기 쉽게 단계별 풀이 과정과 최종 정답을 한국어로 작성하세요.
    """
    
    # 발표를 위해 서버 과부하 시 최대 10번까지 근성 있게 재시도
    max_retries = 10
    for attempt in range(max_retries):
        try:
            # 전략 1: 트래픽이 몰리지 않는 'gemini-3.8-flash-lite' 모델 사용 (필수!)
            response = client.models.generate_content(
                model="gemini-3.8-flash-lite", 
                contents=[prompt, img]
            )
            return response.text.strip()
            
        except errors.ServerError as e: # 구글 서버 에러(503, 429 등) 발생 시
            if attempt < max_retries - 1:
                # 전략 3: 점진적으로 대기 시간 증가 (1.5, 3.0, 4.5...초)
                base_wait = (attempt + 1) * 1.5
                # 전략 4: 랜덤성 추가 (0~0.5초 랜덤 더하기)
                jitter = random.uniform(0, 0.5) 
                wait_time = base_wait + jitter
                
                st.warning(f"🔄 구글 서버 바쁨(503). 발표를 위해 AI가 자동으로 {wait_time:.1f}초 후 다시 시도합니다... (시도 {attempt+2}/{max_retries})")
                time.sleep(wait_time)
                continue
            else:
                st.error("🤯 구글 서버 과부하가 너무 심합니다. 10번 재시도에 실패했습니다. 잠시 후 다시 버튼을 눌러주세요.")
                raise e
        except Exception as e:
            raise e

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
        # 발표를 위해 영구 차단 루프를 st.stop()으로 변경 (앱이 멈추지 않게 함)
        st.stop()
    else:
        st.success("✅ 부정행위 우려가 없습니다. 외부 AI 문제 풀이를 허용합니다.")
        return True

# 메인 화면 UI (발표를 위해 파일 업로드 탭을 기본으로 설정)
uploaded_image = st.file_uploader("테스트할 문제, 시험지, 수험표 사진을 올려주세요", type=["jpg", "jpeg", "png"])
cam_file = st.camera_input("카메라로 사물을 비추고 촬영 버튼을 누르세요 (웹캠 사용 시)")

# 이미지가 업로드되거나 촬영된 경우
target_image = None
if uploaded_image is not None:
    target_image = Image.open(uploaded_image).convert("RGB")
elif cam_file is not None:
    target_image = Image.open(cam_file).convert("RGB")

if target_image is not None:
    # 발표 화면 최적화를 위해 이미지 크기 조정
    st.image(target_image, caption="안경에 포착된 화면", use_container_width=True)
    
    # 버튼 이름도 발표용으로 변경
    if st.button("🔍 AI 윤리 안경 가동 (부정행위 판별 및 풀이)", type="primary"):
        client = genai.Client(api_key=google_api_key)
        
        with st.spinner("AI가 근성 있게 구글 서버에 접속하여 분석 중입니다... (에러 발생 시 자동 재시도)"):
            try:
                # 자동 재시도 기능이 강화된 통합 분석 실행
                full_result = process_image_with_final_retry(client, target_image)
                
                if full_result:
                    lines = full_result.split("\n", 1)
                    first_line = lines[0].strip()
                    solution = lines[1].strip() if len(lines) > 1 else "AI 판단결과 부정행위 우려가 있으므로 문제풀이를 거부합니다"
                    
                    st.write(f"**AI 1차 시각 분석 결과:** `{first_line}`")
                    exam = [item.strip() for item in first_line.split(',')]
                    
                    total = 0
                    is_safe = exam_check(exam, total)
                    
                    if is_safe:
                        st.markdown("### 📝 AI 문제 풀이 결과")
                        st.write(solution)
            except Exception as e:
                st.error("알 수 없는 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
