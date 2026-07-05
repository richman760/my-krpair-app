import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import itertools
from datetime import datetime
import pytz

# ==========================================
# 1. 설정 및 모든 종목 리스트 (원본과 100% 동일)
# ==========================================
KR_NAMES = {
    '005930.KS': '삼성전자', '005935.KS': '삼성전자우', '000660.KS': 'SK하이닉스', '006400.KS': '삼성SDI', '005380.KS': '현대차', '035420.KS': 'NAVER',
    '035720.KS': '카카오', '068270.KS': '셀트리온', '259960.KS': '크래프톤', '005490.KS': 'POSCO홀딩스', '051910.KS': 'LG화학', '015760.KS': '한국전력',
    '066570.KS': 'LG전자', '096530.KS': '씨젠', '247540.KS': '에코프로비엠', '105560.KS': 'KB금융', '017670.KS': 'SK텔레콤', '055550.KS': '신한지주',
    '086520.KS': '에코프로', '034020.KS': '두산에너빌리티', '012330.KS': '현대모비스', '000270.KS': '기아', '032830.KS': '삼성생명', '010950.KS': 'S-Oil',
    '069500.KS': 'KODEX200', '114800.KS': 'KODEX인버스', '009150.KS': '삼성전기', '034220.KS': 'LG디스플레이', '028260.KS': '삼성물산', '003550.KS': 'LG',
    '003490.KS': '대한항공', '090430.KS': '아모레퍼시픽', '018260.KS': '삼성SDS', '009830.KS': '한화솔루션', '011200.KS': 'HMM', '036570.KS': '엔씨소프트',
    '001570.KS': '금양', '028050.KS': '삼성E&A', '078930.KS': '아모레G', '047050.KS': '포스코인터내셔널', '004020.KS': '현대제철', '023590.KS': '다우데이타',
    '010130.KS': '고려아연', '011170.KS': '롯데케미칼', '012450.KS': '한화에어로스페이스', '000720.KS': '현대건설', '005830.KS': 'DB손해보험', '003410.KS': '쌍용C&E',
    '010140.KS': '삼성중공업', '010060.KS': 'OCI홀딩스'
}
WATCH_LIST = list(KR_NAMES.keys())

st.set_page_config(page_title="🇰🇷 5분봉 괴리율 스캐너", layout="wide")

# ==========================================
# 2. UI 및 사이드바 설정
# ==========================================
st.title("🇰🇷 한국 주식 통계적 괴리율(Pairs) 5분봉 스캐너")
st.write("상관관계가 높은 두 종목 중, 한 종목이 비정상적으로 오르거나 내렸을 때 발생하는 **통계적 타점**을 찾아냅니다.")

st.sidebar.header("⚙️ 스캔 설정")
min_correlation = st.sidebar.slider("최소 상관계수 (기본 0.85)", 0.70, 0.99, 0.85, 0.01)
entry_z_score = st.sidebar.slider("진입 Z-Score (기본 2.0)", 1.0, 3.0, 2.0, 0.1)

# ==========================================
# 3. 핵심 데이터 로직 (원본 로직 반영)
# ==========================================
@st.cache_data(ttl=300) 
def scan_pairs(corr_limit, z_limit):
    # 야후 파이낸스 데이터 5일치 5분봉 다운로드
    data = yf.download(WATCH_LIST, period="5d", interval="5m", prepost=False, progress=False)['Close']
    data = data.dropna(axis=1)
    
    tickers_available = data.columns.tolist()
    opportunities = []
    pairs = list(itertools.combinations(tickers_available, 2))
    
    for pair in pairs:
        asset_a, asset_b = pair
        corr = data[asset_a].corr(data[asset_b])
        if corr < corr_limit: 
            continue
            
        ratio = data[asset_a] / data[asset_b]
        mean = ratio.mean()
        std = ratio.std()
        current_z = (ratio.iloc[-1] - mean) / std
        
        if abs(current_z) >= z_limit:
            name_a = KR_NAMES.get(asset_a, asset_a.split('.')[0])
            name_b = KR_NAMES.get(asset_b, asset_b.split('.')[0])
            
            # 추천 등급 마크 부여
            if corr >= 0.95:
                rank_tag = "🥇 1순위 강력추천"
                rank_score = 1
            else:
                rank_tag = "🥈 2순위 일반추천"
                rank_score = 0
                
            # 액션 판단 (Z-score가 양수면 A고평가/B저평가, 음수면 A저평가/B고평가)
            if current_z > 0:
                action = f"➔ [{name_a} 고평가] {name_a} 무시 / ⭐{name_b} 매수(Long)⭐"
            else:
                action = f"➔ [{name_b} 고평가] ⭐{name_a} 매수(Long)⭐ / {name_b} 무시"
            
            opportunities.append({
                '추천등급': rank_tag,
                '페어 (A vs B)': f"{name_a} vs {name_b}",
                '매매전략': action,
                '상관계수': round(corr, 3),
                'Z-Score': round(current_z, 2),
                'A 현재가(₩)': data[asset_a].iloc[-1],
                'B 현재가(₩)': data[asset_b].iloc[-1],
                '_rank_score': rank_score,
                '_abs_z': abs(current_z)
            })
            
    return pd.DataFrame(opportunities), len(tickers_available)

# ==========================================
# 4. 화면 출력 및 버튼
# ==========================================
kst = datetime.now(pytz.timezone('Asia/Seoul'))
st.write(f"🕒 현재 한국 시간: {kst.strftime('%Y-%m-%d %H:%M:%S')}")

if st.button("🚀 괴리율 타점 스캔 시작", use_container_width=True):
    with st.spinner("야후 파이낸스 5분봉 데이터를 다운로드하여 50개 종목의 조합을 탐색 중입니다..."):
        df, available_count = scan_pairs(min_correlation, entry_z_score)
        
        st.info(f"✅ {available_count}개 종목 데이터 확보 완료. 조합 탐색 완료.")
        
        if not df.empty:
            # 1순위(상관도 0.95 이상) 최우선, 그 다음 Z-Score 절대값 큰 순서로 정렬
            df = df.sort_values(by=['_rank_score', '_abs_z'], ascending=[False, False])
            
            # 정렬용 임시 컬럼 삭제
            df = df.drop(columns=['_rank_score', '_abs_z'])
            
            # 가격 컬럼 포맷팅 (원화)
            df['A 현재가(₩)'] = df['A 현재가(₩)'].apply(lambda x: f"₩{int(x):,}")
            df['B 현재가(₩)'] = df['B 현재가(₩)'].apply(lambda x: f"₩{int(x):,}")
            
            st.success(f"🔥 총 {len(df)}개의 확실한 괴리 타점이 발견되었습니다!")
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.warning("⏰ 현재는 모든 종목이 통계적 정상 범위 내에 있습니다. (진입할 괴리 타점 없음)")