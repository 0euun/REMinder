import json
from datetime import date, timedelta

import streamlit as st
import pandas as pd
import altair as alt

import db
import llm

db.init_db()

st.set_page_config(
    page_title="REMinder — 꿈일기",
    page_icon="🌙",
    layout="wide",
)


def check_password() -> bool:
    """secrets.toml의 APP_PASSWORD와 대조하는 단순 비밀번호 게이트."""
    if st.session_state.get("authenticated"):
        return True

    st.title(":material/nights_stay: REMinder")
    app_password = st.secrets.get("APP_PASSWORD", "")
    if not app_password:
        st.error(".streamlit/secrets.toml에 APP_PASSWORD가 설정되어 있지 않습니다.")
        return False

    with st.form("login_form"):
        pw = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("입장")
    if submitted:
        if pw == app_password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    return False


if not check_password():
    st.stop()

DREAM_TYPE_LABELS = {k: v for k, v in db.DREAM_TYPES.items()}
DREAM_TYPE_OPTIONS = list(DREAM_TYPE_LABELS.keys())


# ── 사이드바 ────────────────────────────────────────────────

def sidebar():
    with st.sidebar:
        st.title(":material/nights_stay: REMinder")
        streak = db.get_streak()
        st.metric("연속 기록", f"{streak['streak']}일", help="오늘 포함 연속으로 기록한 일수")
        st.metric("전체 기록", f"{streak['total_days']}일")
        st.divider()

        with st.expander(":material/lightbulb: Reality Check 가이드"):
            st.caption(
                "Reality Check는 '지금 꿈인가?'를 의식적으로 확인하는 자각몽 기법입니다.\n\n"
                "**설정 방법**\n"
                "1. 폰 기본 알림 앱에서 하루 5~10번 반복 알림 설정\n"
                "2. 알림 울릴 때마다 손을 보거나 코를 막고 숨 쉬어보기\n"
                "3. 꿈 기록 시 '어제 Reality Check 횟수'에 결과 기록"
            )
        st.divider()

        return st.radio(
            "메뉴",
            [
                ":material/edit_note: 꿈 기록하기",
                ":material/format_list_bulleted: 꿈 목록",
                ":material/bar_chart: 대시보드",
                ":material/search: 검색",
                ":material/auto_awesome: 드림사인 & 리포트",
            ],
            label_visibility="collapsed",
        )


# ── 꿈 기록 폼 ──────────────────────────────────────────────

def page_record():
    st.header(":material/edit_note: 꿈 기록하기")

    with st.form("dream_form"):
        col1, col2 = st.columns([1, 2])
        with col1:
            dream_date = st.date_input("꿈 날짜", value=date.today())
        with col2:
            dream_type_key = st.selectbox(
                "꿈 타입",
                DREAM_TYPE_OPTIONS,
                format_func=lambda k: DREAM_TYPE_LABELS[k],
            )

        title = st.text_input("제목 (선택)")

        if dream_type_key == "NO_MEMORY":
            st.info("기억이 잘 안 날 때는 마지막 장면, 감정, 색이라도 적어보세요.")

        content = st.text_area(
            "꿈 내용",
            height=200,
            placeholder="기억나는 대로 자유롭게 적어주세요.",
        )

        with st.expander(":material/hotel: 수면 기법 & 컨디션 (선택)"):
            techniques = st.multiselect(
                "어젯밤 시도한 기법",
                db.TECHNIQUES,
                accept_new_options=True,
                help="목록에 없는 기법은 직접 입력 후 Enter로 추가할 수 있습니다.",
            )
            with st.expander(":material/help: 기법 설명 보기"):
                st.markdown(
                    "| 기법 | 설명 |\n|------|------|\n"
                    + "\n".join(
                        f"| **{t}** | {desc} |"
                        for t, desc in db.TECHNIQUE_DESC.items()
                    )
                )
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                sleep_hours = st.number_input(
                    "수면 시간 (h)",
                    min_value=0.0, max_value=24.0, value=0.0, step=0.5,
                    help="0이면 기록 안 함",
                )
                alarm_used = st.checkbox("알람 사용")
            with col_s2:
                caffeine_prev_day = st.checkbox("전날 카페인")
                alcohol_prev_day = st.checkbox("전날 알코올")
            reality_check_count = st.number_input(
                "어제 Reality Check 횟수", min_value=0, max_value=100, value=0, step=1,
            )

        analyze = st.checkbox("저장 후 AI 분석 바로 실행", value=True)
        submitted = st.form_submit_button("저장", use_container_width=True)

    if submitted:
        if not content.strip():
            st.error("꿈 내용을 입력해주세요.")
            return

        dream_id = db.add_dream(
            dream_date=str(dream_date),
            content=content,
            title=title,
            dream_type=dream_type_key,
        )
        st.success(f"저장 완료 (ID: {dream_id})")

        has_condition = (
            bool(techniques) or sleep_hours > 0 or alarm_used
            or caffeine_prev_day or alcohol_prev_day or reality_check_count > 0
        )
        if has_condition:
            db.update_condition(
                dream_id,
                techniques_tried=techniques,
                sleep_hours=float(sleep_hours) if sleep_hours > 0 else None,
                alarm_used=alarm_used,
                caffeine_prev_day=caffeine_prev_day,
                alcohol_prev_day=alcohol_prev_day,
                reality_check_count=int(reality_check_count),
            )

        if dream_type_key == "NO_MEMORY":
            with st.spinner("회상 유도 질문 생성 중…"):
                questions = llm.get_partial_recall_prompt(content)
            st.subheader(":material/psychology: 이런 게 기억나지 않나요?")
            for q in questions:
                st.write(f"- {q}")

        if analyze:
            with st.spinner("AI 분석 중…"):
                result = llm.analyze_dream(content, DREAM_TYPE_LABELS[dream_type_key])
            db.update_analysis(
                dream_id,
                analysis_text=result.get("analysis_text", ""),
                recall_score=result.get("recall_score"),
                recurring_people=result.get("recurring_people", []),
                recurring_places=result.get("recurring_places", []),
                recurring_emotions=result.get("recurring_emotions", []),
            )
            _show_analysis(result)


def _show_analysis(result: dict):
    st.divider()
    st.subheader(":material/auto_fix_high: AI 분석 결과")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(result.get("analysis_text", ""))
    with col2:
        score = result.get("recall_score")
        st.metric("회상 점수", f"{score}/10" if score is not None else "-")

    people = result.get("recurring_people", [])
    places = result.get("recurring_places", [])
    emotions = result.get("recurring_emotions", [])

    if any([people, places, emotions]):
        st.subheader(":material/repeat: 반복 요소")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.caption("인물")
            for p in people:
                st.write(f"• {p}")
        with c2:
            st.caption("장소")
            for p in places:
                st.write(f"• {p}")
        with c3:
            st.caption("감정")
            for e in emotions:
                st.write(f"• {e}")


# ── 꿈 목록 ─────────────────────────────────────────────────

def page_list():
    st.header(":material/format_list_bulleted: 꿈 목록")
    dreams = db.list_dreams(limit=100)

    if not dreams:
        st.info("아직 기록된 꿈이 없습니다.")
        return

    for row in dreams:
        techniques = json.loads(row["techniques_tried"] or "[]")
        technique_tag = f"  [{', '.join(techniques)}]" if techniques else ""
        score_tag = f"  {row['recall_score']}/10점" if row["recall_score"] else ""
        with st.expander(
            f"**{row['dream_date']}** — {row['title'] or '(제목 없음)'}  "
            f"`{DREAM_TYPE_LABELS.get(row['dream_type'], row['dream_type'])}`"
            + score_tag
            + technique_tag
        ):
            st.write(row["content"])

            cond_parts = []
            if row["sleep_hours"]:
                cond_parts.append(f"수면 {row['sleep_hours']}h")
            if row["reality_check_count"]:
                cond_parts.append(f"RC {row['reality_check_count']}회")
            if row["alarm_used"]:
                cond_parts.append("알람 O")
            if row["caffeine_prev_day"]:
                cond_parts.append("카페인 O")
            if row["alcohol_prev_day"]:
                cond_parts.append("알코올 O")
            if cond_parts:
                st.caption(" · ".join(cond_parts))

            if row["analysis_text"]:
                st.divider()
                st.caption("AI 분석")
                st.write(row["analysis_text"])

                people = json.loads(row["recurring_people"] or "[]")
                places = json.loads(row["recurring_places"] or "[]")
                emotions = json.loads(row["recurring_emotions"] or "[]")
                tags = people + places + emotions
                if tags:
                    st.write(" ".join(f"`{t}`" for t in tags))

            col1, col2 = st.columns([1, 5])
            with col1:
                if st.button("삭제", key=f"del_{row['id']}"):
                    db.delete_dream(row["id"])
                    st.rerun()
            with col2:
                if not row["analysis_text"] and st.button(
                    "AI 분석 실행", key=f"analyze_{row['id']}"
                ):
                    with st.spinner("분석 중…"):
                        result = llm.analyze_dream(
                            row["content"],
                            DREAM_TYPE_LABELS.get(row["dream_type"], row["dream_type"]),
                        )
                    db.update_analysis(
                        row["id"],
                        analysis_text=result.get("analysis_text", ""),
                        recall_score=result.get("recall_score"),
                        recurring_people=result.get("recurring_people", []),
                        recurring_places=result.get("recurring_places", []),
                        recurring_emotions=result.get("recurring_emotions", []),
                    )
                    st.rerun()


# ── 캘린더 히트맵 헬퍼 ──────────────────────────────────────

def _calendar_chart(
    data: list[dict], date_col: str, value_col: str, color_scheme: str = "greens"
) -> alt.Chart:
    end = date.today()
    start = end - timedelta(days=364)
    df_all = pd.DataFrame({"d": pd.date_range(start.isoformat(), end.isoformat())})
    if data:
        df_data = pd.DataFrame(data)
        df_data["d"] = pd.to_datetime(df_data[date_col])
        df = df_all.merge(df_data[["d", value_col]], on="d", how="left")
    else:
        df = df_all.copy()
        df[value_col] = 0
    df[value_col] = df[value_col].fillna(0)
    df["week"] = ((df["d"] - pd.Timestamp(start)).dt.days // 7)
    df["day"] = df["d"].dt.dayofweek  # 0=월
    df["date_str"] = df["d"].dt.strftime("%Y-%m-%d")
    return (
        alt.Chart(df)
        .mark_rect(cornerRadius=2)
        .encode(
            x=alt.X("week:O", axis=None),
            y=alt.Y(
                "day:O",
                sort=list(range(7)),
                axis=alt.Axis(
                    labelExpr="['월','화','수','목','금','토','일'][datum.value]",
                    title=None,
                ),
            ),
            color=alt.Color(
                f"{value_col}:Q",
                scale=alt.Scale(scheme=color_scheme),
                legend=None,
            ),
            tooltip=["date_str:N", alt.Tooltip(f"{value_col}:Q")],
        )
        .properties(height=130)
    )


# ── 대시보드 ─────────────────────────────────────────────────

def page_dashboard():
    st.header(":material/bar_chart: 대시보드")

    tab1, tab2, tab3 = st.tabs([
        ":material/show_chart: 점수 & 분포",
        ":material/calendar_month: 캘린더",
        ":material/track_changes: 기법 & 컨디션",
    ])

    # ── Tab 1: 점수 & 분포 ──────────────────────────────────
    with tab1:
        trend = db.get_recall_trend(days=30)
        type_dist = db.get_type_distribution()
        lucid_trend = db.get_lucid_trend(months=6)

        if not trend and not type_dist:
            st.info("아직 데이터가 부족합니다. 꿈을 더 기록해보세요!")
        else:
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("회상 점수 추이 (최근 30일)")
                if trend:
                    df = pd.DataFrame(trend)
                    chart = (
                        alt.Chart(df)
                        .mark_line(point=True)
                        .encode(
                            x=alt.X("dream_date:T", title="날짜"),
                            y=alt.Y("avg_score:Q", scale=alt.Scale(domain=[0, 10]), title="평균 점수"),
                            tooltip=["dream_date:T", "avg_score:Q", "cnt:Q"],
                        )
                        .properties(height=250)
                    )
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.info("회상 점수 데이터가 없습니다.")

            with col2:
                st.subheader("꿈 타입 분포")
                if type_dist:
                    df = pd.DataFrame(type_dist)
                    df["label"] = df["dream_type"].map(lambda k: DREAM_TYPE_LABELS.get(k, k))
                    chart = (
                        alt.Chart(df)
                        .mark_arc()
                        .encode(
                            theta=alt.Theta("cnt:Q"),
                            color=alt.Color("label:N", legend=alt.Legend(title="타입")),
                            tooltip=["label:N", "cnt:Q"],
                        )
                        .properties(height=250)
                    )
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.info("타입 분포 데이터가 없습니다.")

        st.subheader("자각몽 빈도 (월별, 최근 6개월)")
        if lucid_trend:
            df = pd.DataFrame(lucid_trend)
            chart = (
                alt.Chart(df)
                .mark_bar()
                .encode(
                    x=alt.X("month:N", title="월"),
                    y=alt.Y("lucid_cnt:Q", title="자각몽 횟수"),
                    tooltip=["month:N", "lucid_cnt:Q", "total_cnt:Q"],
                )
                .properties(height=220)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("자각몽 데이터가 없습니다.")

    # ── Tab 2: 캘린더 ────────────────────────────────────────
    with tab2:
        activity = db.get_activity_calendar(days=365)
        lucid_cal = db.get_lucid_calendar(days=365)

        st.subheader("기록 캘린더 (최근 1년)")
        st.altair_chart(_calendar_chart(activity, "dream_date", "cnt", "greens"), use_container_width=True)

        st.subheader("자각몽 발생 캘린더 (최근 1년)")
        lucid_only = [r for r in lucid_cal if r["is_lucid"]]
        st.altair_chart(_calendar_chart(lucid_only, "dream_date", "is_lucid", "oranges"), use_container_width=True)

    # ── Tab 3: 기법 & 컨디션 ─────────────────────────────────
    with tab3:
        technique_stats = db.get_technique_stats()
        condition_data = db.get_condition_recall_stats()

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("기법별 사용 & 자각몽 연관율")
            if technique_stats:
                df_t = pd.DataFrame(technique_stats).sort_values("used", ascending=False)
                c1 = (
                    alt.Chart(df_t)
                    .mark_bar()
                    .encode(
                        x=alt.X("used:Q", title="사용 횟수"),
                        y=alt.Y("technique:N", sort="-x", title=""),
                        color=alt.value("#4c78a8"),
                        tooltip=["technique:N", "used:Q", "lucid:Q",
                                 alt.Tooltip("lucid_rate:Q", title="자각몽율(%)")],
                    )
                    .properties(height=200, title="기법별 사용 횟수")
                )
                c2 = (
                    alt.Chart(df_t)
                    .mark_bar()
                    .encode(
                        x=alt.X("lucid_rate:Q", title="자각몽 발생률 (%)"),
                        y=alt.Y("technique:N", sort="-x", title=""),
                        color=alt.value("#f58518"),
                        tooltip=["technique:N", alt.Tooltip("lucid_rate:Q", title="자각몽율(%)")],
                    )
                    .properties(height=200, title="기법별 자각몽율 (%)")
                )
                st.altair_chart(c1, use_container_width=True)
                st.altair_chart(c2, use_container_width=True)
            else:
                st.info("기법 데이터가 없습니다.\n꿈 기록 시 '수면 기법 & 컨디션' 섹션을 작성해보세요.")

        with col2:
            st.subheader("컨디션 & 회상 점수")
            if condition_data:
                df_c = pd.DataFrame(condition_data)
                df_scored = df_c[df_c["recall_score"].notna()].copy()

                df_sleep = df_scored[
                    df_scored["sleep_hours"].notna() & (df_scored["sleep_hours"] > 0)
                ].copy()
                if not df_sleep.empty:
                    bins = [0, 5, 6, 7, 8, 9, 25]
                    labels = ["~5h", "5~6h", "6~7h", "7~8h", "8~9h", "9h+"]
                    df_sleep["bucket"] = pd.cut(
                        df_sleep["sleep_hours"], bins=bins, labels=labels, right=False
                    )
                    grouped = (
                        df_sleep.groupby("bucket", observed=True)["recall_score"]
                        .mean()
                        .reset_index()
                    )
                    grouped.columns = ["수면시간", "avg"]
                    chart = (
                        alt.Chart(grouped)
                        .mark_bar()
                        .encode(
                            x=alt.X("수면시간:N"),
                            y=alt.Y("avg:Q", scale=alt.Scale(domain=[0, 10]), title="평균 회상 점수"),
                            color=alt.value("#5ba4cf"),
                            tooltip=["수면시간:N", alt.Tooltip("avg:Q", format=".1f")],
                        )
                        .properties(height=180, title="수면 시간별 평균 회상 점수")
                    )
                    st.altair_chart(chart, use_container_width=True)

                rows = []
                for col_name, label in [
                    ("caffeine_prev_day", "카페인"),
                    ("alcohol_prev_day", "알코올"),
                    ("alarm_used", "알람"),
                ]:
                    sub = df_scored[df_scored[col_name].notna()]
                    if sub.empty:
                        continue
                    avg_yes = sub[sub[col_name] == 1]["recall_score"].mean()
                    avg_no = sub[sub[col_name] == 0]["recall_score"].mean()
                    if not pd.isna(avg_yes):
                        rows.append({"요인": f"{label} O", "avg": round(float(avg_yes), 1)})
                    if not pd.isna(avg_no):
                        rows.append({"요인": f"{label} X", "avg": round(float(avg_no), 1)})

                if rows:
                    df_comp = pd.DataFrame(rows)
                    chart = (
                        alt.Chart(df_comp)
                        .mark_bar()
                        .encode(
                            x=alt.X("avg:Q", scale=alt.Scale(domain=[0, 10]), title="평균 회상 점수"),
                            y=alt.Y("요인:N", sort="-x"),
                            color=alt.value("#e45756"),
                            tooltip=["요인:N", "avg:Q"],
                        )
                        .properties(height=200, title="컨디션별 평균 회상 점수")
                    )
                    st.altair_chart(chart, use_container_width=True)

                df_rc = df_c[df_c["reality_check_count"] > 0].copy()
                if not df_rc.empty and df_rc["is_lucid"].notna().any():
                    st.caption("Reality Check 횟수별 자각몽 발생율")
                    bins_rc = [0, 3, 6, 10, 100]
                    labels_rc = ["1~2회", "3~5회", "6~9회", "10회+"]
                    df_rc["rc_bucket"] = pd.cut(
                        df_rc["reality_check_count"], bins=bins_rc, labels=labels_rc, right=False
                    )
                    grouped_rc = (
                        df_rc.groupby("rc_bucket", observed=True)["is_lucid"]
                        .mean()
                        .reset_index()
                    )
                    grouped_rc.columns = ["RC 횟수", "자각몽율"]
                    grouped_rc["자각몽율"] = (grouped_rc["자각몽율"] * 100).round(1)
                    chart = (
                        alt.Chart(grouped_rc)
                        .mark_bar()
                        .encode(
                            x=alt.X("RC 횟수:N"),
                            y=alt.Y("자각몽율:Q", title="자각몽 발생율 (%)"),
                            color=alt.value("#72b7b2"),
                            tooltip=["RC 횟수:N", "자각몽율:Q"],
                        )
                        .properties(height=180)
                    )
                    st.altair_chart(chart, use_container_width=True)
            else:
                st.info("컨디션 데이터가 없습니다.\n꿈 기록 시 '수면 기법 & 컨디션' 섹션을 작성해보세요.")


# ── 검색 ─────────────────────────────────────────────────────

def page_search():
    st.header(":material/search: 검색")

    col1, col2 = st.columns([4, 1])
    with col1:
        query = st.text_input("검색어", placeholder="예: 바다, 가족, 하늘을 나는 꿈…")
    with col2:
        use_ai = st.toggle("AI 의미 검색", value=False, help="AI가 의미상 관련된 꿈도 함께 찾습니다.")

    if not query.strip():
        st.info("검색어를 입력하세요.")
        return

    if use_ai:
        with st.spinner("AI가 관련 꿈을 분석 중…"):
            all_rows = db.list_dreams(limit=500)
            all_dreams = [dict(r) for r in all_rows]
            matched_ids = set(llm.search_by_meaning(query, all_dreams))
            results = [d for d in all_dreams if d["id"] in matched_ids]
    else:
        results = db.search_dreams(query)

    if not results:
        st.info("검색 결과가 없습니다.")
        return

    st.caption(f"{len(results)}개 발견")
    for row in results:
        score_tag = f"  {row['recall_score']}/10점" if row.get("recall_score") else ""
        with st.expander(
            f"**{row['dream_date']}** — {row['title'] or '(제목 없음)'}  "
            f"`{DREAM_TYPE_LABELS.get(row['dream_type'], row['dream_type'])}`"
            + score_tag
        ):
            st.write(row["content"])
            if row.get("analysis_text"):
                st.divider()
                st.caption(row["analysis_text"])


# ── 드림사인 & 리포트 ─────────────────────────────────────────

def page_dream_signs():
    st.header(":material/auto_awesome: 드림사인 & 리포트")

    tab1, tab2, tab3 = st.tabs([
        ":material/psychology: 드림사인 Top 5",
        ":material/bedtime: MILD 인텐션",
        ":material/summarize: 주간 리포트",
    ])

    # ── Tab 1: 드림사인 클러스터링 ──────────────────────────
    with tab1:
        st.subheader("나만의 드림사인 Top 5")
        st.caption("AI가 꿈에서 반복적으로 나타나는 패턴을 분석해 그룹화합니다.")

        elements = db.get_all_recurring_elements()
        if elements:
            from collections import Counter
            freq_preview = Counter(elements).most_common(10)
            st.caption(
                "추출된 요소 상위 10개: "
                + ", ".join(f"{e}({c})" for e, c in freq_preview)
            )
        else:
            st.warning("아직 AI 분석된 꿈이 없습니다. 꿈을 기록하고 AI 분석을 먼저 실행해보세요.")

        if st.button("드림사인 분석 실행", use_container_width=True, disabled=not elements):
            with st.spinner(f"총 {len(elements)}개 요소 클러스터링 중…"):
                result = llm.cluster_dream_signs(elements)
            st.session_state["dream_signs_result"] = result

        if "dream_signs_result" in st.session_state:
            signs = st.session_state["dream_signs_result"].get("dream_signs", [])
            err = st.session_state["dream_signs_result"].get("error")
            if err:
                st.error(f"오류: {err}")
            elif signs:
                for i, sign in enumerate(signs, 1):
                    with st.expander(
                        f"#{i} **{sign['sign']}** — {sign.get('description', '')}  (총 {sign.get('count', '?')}회)"
                    ):
                        elems = sign.get("elements", [])
                        if elems:
                            st.write(" ".join(f"`{e}`" for e in elems))
            else:
                st.info("드림사인을 찾지 못했습니다. 꿈이 더 쌓이면 다시 시도해보세요.")

    # ── Tab 2: MILD 인텐션 ──────────────────────────────────
    with tab2:
        st.subheader("오늘 밤 MILD 인텐션")

        elements = db.get_all_recurring_elements()
        from collections import Counter
        top_signs = [e for e, _ in Counter(elements).most_common(5)] if elements else []

        custom_signs = st.text_input(
            "드림사인 (쉼표 구분, 직접 수정 가능)",
            value=", ".join(top_signs),
            placeholder="예: 학교, 가족, 높은 곳",
        )

        if st.button("인텐션 문장 생성", use_container_width=True):
            signs_list = [s.strip() for s in custom_signs.split(",") if s.strip()]
            with st.spinner("생성 중…"):
                intention = llm.generate_mild_intention(signs_list)
            st.session_state["mild_intention"] = intention

        if "mild_intention" in st.session_state:
            st.info(st.session_state["mild_intention"])
            st.caption("잠들기 전 이 문장을 10번 천천히 되뇌어보세요.")

    # ── Tab 3: 주간 리포트 ──────────────────────────────────
    with tab3:
        st.subheader("주간 요약 리포트")

        week_offset = st.selectbox(
            "기간",
            [0, 1, 2, 3],
            format_func=lambda x: ["이번 주 (최근 7일)", "지난주", "2주 전", "3주 전"][x],
        )

        if st.button("리포트 생성", use_container_width=True):
            dreams = db.get_weekly_dreams(offset_days=week_offset * 7)
            if not dreams:
                st.warning("해당 기간에 기록된 꿈이 없습니다.")
            else:
                with st.spinner(f"꿈 {len(dreams)}개 분석 중…"):
                    summary = llm.summarize_week(dreams)
                st.session_state["weekly_summary"] = summary
                st.session_state["weekly_summary_cnt"] = len(dreams)

        if "weekly_summary" in st.session_state:
            st.caption(f"꿈 {st.session_state['weekly_summary_cnt']}개 분석")
            st.write(st.session_state["weekly_summary"])


# ── 진입점 ───────────────────────────────────────────────────

page = sidebar()

if page.endswith("꿈 기록하기"):
    page_record()
elif page.endswith("꿈 목록"):
    page_list()
elif page.endswith("대시보드"):
    page_dashboard()
elif page.endswith("검색"):
    page_search()
elif page.endswith("드림사인 & 리포트"):
    page_dream_signs()
