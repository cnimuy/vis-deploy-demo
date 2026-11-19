"""지점 실적의 격차를 추적하는 Streamlit 대시보드."""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


DATA_PATH = Path(__file__).with_name("sales.csv")
COLORS = {"A": "#087c73", "B": "#ba4b32"}
METRICS = {"매출": "sales", "영업이익": "profit"}
MONTHS = list(range(1, 13))

st.set_page_config(page_title="월간 실적 지도", page_icon="📊", layout="wide")
st.markdown(
    """
    <style>
    .block-container {max-width: 1320px; padding-top: 3rem; padding-bottom: 3rem;}
    .stApp {background: #f5f3ee; color: #202c2a;}
    .stApp h1, .stApp h2, .stApp h3 {color: #202c2a;}
    [data-testid="stSidebar"] {background: #e9eee7;}
    [data-testid="stSidebar"] :is(p, label, h2, h3) {color: #202c2a;}
    [data-testid="stMetric"] {
        background: #fffefa; border: 1px solid #d9ded4; border-radius: 14px;
        padding: 0.9rem 1.05rem; height: 100%;
    }
    [data-testid="stMetric"] :is(p, span, div) {color: #202c2a;}
    [data-testid="stCaptionContainer"] p {color: #54645e;}
    .report-cover {
        background: #163d37; border-radius: 20px; padding: clamp(20px, 4vw, 46px);
        color: #fffdf5; margin-bottom: 1rem;
    }
    .report-cover h1 {color: #fffdf5; font-size: clamp(2rem, 4vw, 3.45rem);
        letter-spacing: -0.045em; padding: .25em 0 .3em;}
    .report-cover p {color: #e2eee5; margin: 0; max-width: 620px;}
    .report-cover .edition {color: #b9dbcc; font-size: .85rem; font-weight: 650;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def read_sales(modified_at):
    return pd.read_csv(DATA_PATH)


def format_chart(figure, months, y_title):
    figure.update_layout(
        template="plotly_white",
        paper_bgcolor="#fffefa",
        plot_bgcolor="#fffefa",
        font={"color": "#253632", "family": "Apple SD Gothic Neo, Malgun Gothic, sans-serif"},
        margin={"l": 18, "r": 25, "t": 45, "b": 18},
        legend={"orientation": "h", "y": 1.17, "x": 0},
        height=320,
        hoverlabel={"bgcolor": "#fffefa", "font_color": "#253632"},
    )
    figure.update_xaxes(tickmode="array", tickvals=months, ticksuffix="월", title=None)
    figure.update_yaxes(title=y_title, gridcolor="#e6e9e1", zerolinecolor="#778680")
    return figure


def draw(figure):
    st.plotly_chart(figure, theme=None, width="stretch", config={"displayModeBar": False})


st.markdown(
    """
    <div class="report-cover">
      <p class="edition">2026 · 지점 실적 리포트</p>
      <h1>실적 격차는<br>어느 달에 벌어졌을까?</h1>
      <p>월별 실적과 누적 격차를 함께 보고, 전체 결과를 가장 크게 움직인 달을 찾아보세요.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption("수업용 가상 데이터 · 2026년 1–12월 · 금액 단위 백만원")

try:
    data = read_sales(DATA_PATH.stat().st_mtime_ns)
except FileNotFoundError:
    st.error("app.py와 같은 폴더에 sales.csv를 올려 주세요.")
    st.stop()

st.sidebar.header("조회 조건")
branches = st.sidebar.multiselect("지점", list(COLORS), default=list(COLORS))
start, end = st.sidebar.slider("월 범위", 1, 12, (1, 12))
metric_label = st.sidebar.radio("표시 지표", list(METRICS), horizontal=True)
metric = METRICS[metric_label]
view = data.loc[data["branch"].isin(branches) & data["month"].between(start, end)]

if view.empty:
    st.warning("표시할 데이터가 없습니다. 지점을 하나 이상 선택해 주세요.")
    st.stop()

months = MONTHS[start - 1 : end]
totals = view.groupby("branch")[metric].sum()
monthly = (
    view.groupby(["month", "branch"])[metric]
    .sum()
    .unstack()
    .reindex(index=months, columns=branches)
)
selected_sales = view["sales"].sum()
margin = view["profit"].sum() / selected_sales * 100 if selected_sales else None

st.subheader(f"{start}–{end}월 {metric_label} · {', '.join(branches)}지점")
amount, count, rate = st.columns(3)
amount.metric(f"{metric_label} 합계", f"{view[metric].sum():,.0f} 백만원")
count.metric("표시 관측 수", f"{len(view)}행")
rate.metric("영업이익률", f"{margin:.1f}%" if margin is not None else "—")

gap = None
if {"A", "B"}.issubset(totals.index):
    # Only compare months with observations for both branches.
    paired = monthly.dropna(subset=["A", "B"])
    if not paired.empty:
        gap = paired["A"] - paired["B"]
        cumulative = gap.cumsum()
        peak_month = int(gap.abs().idxmax())
        final_gap = cumulative.iloc[-1]
        if final_gap:
            leader = "A" if final_gap > 0 else "B"
            summary = f"공통 관측 월 합계에서 **{leader}지점이 {abs(final_gap):,.0f}백만원 앞서요.**"
        else:
            summary = "공통 관측 월의 두 지점 합계가 같아요."
        if gap.abs().max():
            summary += f" 월별 격차가 가장 컸던 달은 **{peak_month}월({abs(gap.loc[peak_month]):,.0f}백만원)**이에요."
        st.info(summary)

st.markdown("### 월별 실적")
trend = go.Figure()
for branch in branches:
    trend.add_scatter(
        x=months, y=monthly[branch], mode="lines+markers", name=f"{branch}지점",
        line={"color": COLORS[branch], "width": 3}, marker={"size": 7},
        hovertemplate=f"%{{x}}월 · {branch}지점 %{{y:,.0f}}백만원<extra></extra>",
    )
draw(format_chart(trend, months, f"{metric_label} (백만원)"))

if gap is not None:
    st.markdown("### 격차가 쌓이는 과정")
    focus = st.selectbox(
        "자세히 볼 달", options=list(gap.index), index=list(gap.index).index(peak_month),
        format_func=lambda month: f"{month}월", key=f"focus-{start}-{end}-{metric}",
    )
    focus_gap = gap.loc[focus]
    st.caption(
        f"{focus}월 · A {monthly.loc[focus, 'A']:,.0f} / B {monthly.loc[focus, 'B']:,.0f}백만원"
        f" · 월 격차 {focus_gap:+,.0f} · 누적 격차 {cumulative.loc[focus]:+,.0f}백만원"
    )
    left, right = st.columns(2)
    with left:
        st.markdown("**월별 격차**")
        st.caption("A−B. 0 위는 A 우세, 0 아래는 B 우세.")
        bars = go.Figure(go.Bar(
            x=gap.index, y=gap,
            marker_color=[COLORS["A"] if value >= 0 else COLORS["B"] for value in gap],
            marker_opacity=[1 if month == focus else 0.6 for month in gap.index],
            hovertemplate="%{x}월 · A−B %{y:+,.0f}백만원<extra></extra>",
        ))
        draw(format_chart(bars, months, "월별 차이 (백만원)"))
    with right:
        st.markdown("**누적 격차**")
        st.caption("선택 기간의 첫 달부터 월별 차이를 합산해요.")
        running = go.Figure(go.Scatter(
            x=cumulative.index, y=cumulative, mode="lines+markers",
            line={"color": "#253632", "width": 3}, marker={"size": 6},
            hovertemplate="%{x}월까지 · A−B %{y:+,.0f}백만원<extra></extra>",
        ))
        running.add_scatter(
            x=[focus], y=[cumulative.loc[focus]], mode="markers",
            marker={"size": 13, "color": "#7b5b15"}, showlegend=False, hoverinfo="skip",
        )
        running.add_hline(y=0, line_dash="dot", line_color="#778680")
        running.update_layout(showlegend=False)
        draw(format_chart(running, months, "누적 차이 (백만원)"))
else:
    # With a single branch selected, show that branch's performance drivers.
    left, right = st.columns(2)
    by_month = view.groupby("month")[["sales", "profit"]].sum().reindex(months)
    with left:
        st.markdown("**기간 누적 실적**")
        accumulated = go.Figure(go.Scatter(
            x=months, y=by_month[metric].cumsum(), mode="lines+markers",
            line={"color": COLORS[branches[0]], "width": 3}, fill="tozeroy",
        ))
        draw(format_chart(accumulated, months, "누적 금액 (백만원)"))
    with right:
        st.markdown("**월별 영업이익률**")
        rates = by_month["profit"].div(by_month["sales"].where(by_month["sales"].ne(0))) * 100
        rate_chart = go.Figure(go.Bar(x=months, y=rates, marker_color=COLORS[branches[0]]))
        draw(format_chart(rate_chart, months, "영업이익률 (%)"))

with st.expander("선택한 데이터 보기 및 CSV 저장"):
    st.dataframe(
        view.sort_values(["month", "branch"]), hide_index=True, width="stretch",
        column_config={
            "month": "월", "branch": "지점",
            "sales": "매출 (백만원)", "profit": "영업이익 (백만원)",
        },
    )
    st.download_button(
        "현재 선택 CSV 저장",
        data=view.sort_values(["month", "branch"]).to_csv(index=False).encode("utf-8-sig"),
        file_name="selected_sales.csv", mime="text/csv",
    )
