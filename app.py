import random
import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="나와 잘 맞는 철학자 찾기", page_icon="🏛️", layout="centered"
)

# 1. 철학자 데이터 (이름, 설명, 대표 명언, 어울리는 키워드)
PHILOSOPHERS = {
    "소크라테스": {
        "desc": "끊임없이 질문하고 스스로의 무지를 깨달으며 본질과 진리를 탐구하는 타입입니다.",
        "quote": '"너 자신을 알라."',
        "tag": "#본질탐구 #질문왕 #논리적사색",
    },
    "니체": {
        "desc": "기존의 틀과 관습을 깨고 나만의 가치를 창조하며 자신의 운명을 개척하는 타입입니다.",
        "quote": '"나를 죽이지 못하는 고통은 나를 더 강하게 만든다."',
        "tag": "#자기초월 #주체적삶 #개척자",
    },
    "공자": {
        "desc": "사람 간의 도리와 배려를 중시하며 공동체의 조화로운 삶을 추구하는 타입입니다.",
        "quote": '"내가 원하지 않는 바를 남에게 행하지 말라."',
        "tag": "#인간관계 #배려와조화 #원칙주의",
    },
    "장자": {
        "desc": "세상의 기준이나 타인의 시선에 얽매이지 않고 자연의 흐름대로 자유롭게 사는 타입입니다.",
        "quote": '"세상의 잣대로 나를 재단하지 마라."',
        "tag": "#자유로운영혼 #무위자연 #마음의평화",
    },
    "아리스토텔레스": {
        "desc": "한쪽으로 치우친 극단을 피하고 균형(중용)을 지키며 현실적인 성장을 추구하는 타입입니다.",
        "quote": '"우리는 반복적으로 하는 행동의 결과물이다. 탁월함은 행동이 아닌 습관이다."',
        "tag": "#중용의미덕 #현실주의 #꾸준한성장",
    },
}

# 2. 질문 및 선택지 데이터
QUESTIONS = [
    {
        "q": "Q1. 친구와 의견이 다를 때 나의 행동은?",
        "options": {
            "왜 그렇게 생각하는지 끝까지 질문을 던져본다.": "소크라테스",
            "내 소신이 맞다면 밀어붙이고 새로운 방향을 제시한다.": "니체",
            "서로의 입장을 배려하며 원만하게 합의점을 찾는다.": "공자",
            "다툴 필요 있나? 각자 생각대로 살면 된다고 넘긴다.": "장자",
        },
    },
    {
        "q": "Q2. 나에게 '행복'이란 무엇인가?",
        "options": {
            "나를 돌아보고 내면의 지혜를 쌓아가는 과정": "소크라테스",
            "시련을 이겨내고 어제보다 더 강해지는 것": "니체",
            "좋은 습관을 들이고 균형 잡힌 일상을 사는 것": "아리스토텔레스",
            "아무런 걱정이나 구속 없이 마음이 편안한 상태": "장자",
        },
    },
    {
        "q": "Q3. 사회의 규칙이나 관습을 바라보는 시선은?",
        "options": {
            "공동체의 질서와 조화를 위해 반드시 지켜야 한다.": "공자",
            "낡은 관습은 부수고 나만의 새로운 기준을 세워야 한다.": "니체",
            "상황에 맞게 지나치지도 모자라지도 않게 적용해야 한다.": "아리스토텔레스",
            "인간이 만든 인위적인 틀일 뿐, 너무 얽매일 필요 없다.": "장자",
        },
    },
    {
        "q": "Q4. 주말에 가장 하고 싶은 활동은?",
        "options": {
            "조용히 책을 읽거나 사색에 잠기기": "소크라테스",
            "새로운 목표를 세우고 자기계발하기": "아리스토텔레스",
            "가족이나 친구들과 모여 맛있는 음식 나누기": "공자",
            "계획 없이 발길 닿는 대로 산책하거나 낮잠 자기": "장자",
        },
    },
    {
        "q": "Q5. 인생에서 큰 실패를 겪었을 때 나의 반응은?",
        "options": {
            "내가 무엇을 몰랐는지 원인을 냉정하게 분석한다.": "소크라테스",
            "이 시련조차 내 성장의 밑거름이라며 다시 일어난다.": "니체",
            "실패에서 교훈을 얻어 다음엔 더 현실적인 계획을 세운다.": "아리스토텔레스",
            "인생사 새옹지마, 마음을 비우고 훌훌 털어버린다.": "장자",
        },
    },
]

# 세션 상태 초기화 (페이지가 새로고침 되어도 진행 상태 유지)
if "step" not in st.session_state:
  st.session_state.step = 0
if "scores" not in st.session_state:
  st.session_state.scores = {name: 0 for name in PHILOSOPHERS}


def reset_test():
  st.session_state.step = 0
  st.session_state.scores = {name: 0 for name in PHILOSOPHERS}


# --- UI 렌더링 시작 ---
st.title("🏛️ 나와 가장 잘 맞는 철학자 찾기")
st.caption("5가지 질문을 통해 당신의 삶의 태도와 닮은 철학자를 알아보세요.")
st.divider()

total_q = len(QUESTIONS)
current_step = st.session_state.step

# 3. 질문 진행 화면
if current_step < total_q:
  # 진행률 바
  progress = current_step / total_q
  st.progress(progress, text=f"진행률: {current_step} / {total_q}")

  q_data = QUESTIONS[current_step]
  st.subheader(q_data["q"])
  st.write("")  # 여백

  # 선택지 라디오 버튼
  choice = st.radio(
      "가장 가까운 답변을 선택하세요:",
      list(q_data["options"].keys()),
      key=f"radio_{current_step}",
  )

  st.write("")
  col1, col2 = st.columns([1, 5])
  with col1:
    if st.button("다음 ➡️", type="primary", use_container_width=True):
      selected_phil = q_data["options"][choice]
      st.session_state.scores[selected_phil] += 1
      st.session_state.step += 1
      st.rerun()

# 4. 최종 결과 화면
else:
  st.progress(1.0, text="분석 완료! 🎉")

  # 최고 점수 계산 (동점일 경우 랜덤 선택)
  scores = st.session_state.scores
  max_score = max(scores.values())
  top_philosophers = [k for k, v in scores.items() if v == max_score]
  best_match = random.choice(top_philosophers)
  info = PHILOSOPHERS[best_match]

  # 결과 카드 UI
  st.balloons()
  st.success("당신의 영혼의 단짝 철학자를 찾았습니다!")

  with st.container(border=True):
    st.markdown(f"### 🏆 당신과 닮은 철학자: **{best_match}**")
    st.markdown(f"**{info['tag']}**")
    st.info(f"💬 {info['quote']}")
    st.write(info["desc"])

  st.write("")
  st.subheader("📊 내 안의 철학자 성향 분포")
  # Streamlit 내장 막대그래프로 점수 시각화
  st.bar_chart(scores)

  st.write("")
  if st.button("🔄 테스트 다시 하기", use_container_width=True):
    reset_test()
    st.rerun()
