import datetime
import random
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="本田精密工業 - 生産管理システム（生産管理全注文可視化版）",
    layout="wide",
)

st.title(
    "本田精密工業 - マルチビュー生産管理システム（生産管理全注文一覧・キャパ可視化対応）"
)

# --- 1. 稼働日計算ユーティリティ関数 ---
HOLIDAYS_2026 = [
    "2026-01-01",
    "2026-01-12",
    "2026-02-11",
    "2026-02-23",
    "2026-03-20",
    "2026-04-29",
    "2026-05-03",
    "2026-05-04",
    "2026-05-05",
    "2026-05-06",
    "2026-07-20",
    "2026-08-11",
    "2026-09-21",
    "2026-09-22",
    "2026-09-23",
    "2026-10-12",
    "2026-11-03",
    "2026-11-23",
]


def add_working_hours(start_dt, hours_to_add, work_saturday=False):
  current = start_dt

  def align_to_worktime(dt):
    while True:
      date_str = dt.strftime("%Y-%m-%d")
      weekday = dt.weekday()
      is_holiday = date_str in HOLIDAYS_2026

      if (
          weekday == 6
          or is_holiday
          or (weekday == 5 and not work_saturday)
      ):
        dt = (dt + datetime.timedelta(days=1)).replace(
            hour=8, minute=0, second=0
        )
        continue
      if dt.hour < 8:
        dt = dt.replace(hour=8, minute=0, second=0)
      if dt.hour >= 17:
        dt = (dt + datetime.timedelta(days=1)).replace(
            hour=8, minute=0, second=0
        )
        continue
      break
    return dt

  current = align_to_worktime(current)
  remaining_hours = hours_to_add

  while remaining_hours > 0:
    current = align_to_worktime(current)
    today_end = current.replace(hour=17, minute=0, second=0)
    available_today = (today_end - current).total_seconds() / 3600.0

    if remaining_hours <= available_today:
      current = current + datetime.timedelta(hours=remaining_hours)
      remaining_hours = 0
    else:
      remaining_hours -= available_today
      current = (current + datetime.timedelta(days=1)).replace(
          hour=8, minute=0, second=0
      )

  return current


# --- 2. 工程マスターデータ ---
default_process_master = [
    {
        "工程順序": 1,
        "工程名": "1. ブランク発注",
        "区分": "社外",
        "設備台数": 99,
        "リードタイム(日)": 2.0,
        "本あたり時間(分)": 0,
        "色": "#8c564b",
        "公式設備・備考": "外部サプライヤー手配",
    },
    {
        "工程順序": 2,
        "工程名": "2. ブランク製作(社外)",
        "区分": "社外",
        "設備台数": 99,
        "リードタイム(日)": 21.0,
        "本あたり時間(分)": 0,
        "色": "#e377c2",
        "公式設備・備考": "外注素材加工 (21日)",
    },
    {
        "工程順序": 3,
        "工程名": "3. ブランク完成・受入",
        "区分": "社内",
        "設備台数": 5,
        "リードタイム(日)": 0.0,
        "本あたり時間(分)": 2,
        "色": "#7f7f7f",
        "公式設備・備考": "受入検査台・測定器",
    },
    {
        "工程順序": 4,
        "工程名": "4. 社内成型(MC)",
        "区分": "社内",
        "設備台数": 18,
        "リードタイム(日)": 0.0,
        "本あたり時間(分)": 15,
        "色": "#1f77b4",
        "公式設備・備考": "牧野フライス精機等 (計18台)",
    },
    {
        "工程順序": 5,
        "工程名": "5. 溝加工",
        "区分": "社内",
        "設備台数": 16,
        "リードタイム(日)": 0.0,
        "本あたり時間(分)": 40,
        "色": "#aec7e8",
        "公式設備・備考": "ROLLOMATIC (計16台)",
    },
    {
        "工程順序": 6,
        "工程名": "6. 外周刃加工",
        "区分": "社内",
        "設備台数": 16,
        "リードタイム(日)": 0.0,
        "本あたり時間(分)": 30,
        "色": "#2ca02c",
        "公式設備・備考": "ANCA TX7等 (計16台)",
    },
    {
        "工程順序": 7,
        "工程名": "7. 底刃加工",
        "区分": "社内",
        "設備台数": 15,
        "リードタイム(日)": 0.0,
        "本あたり時間(分)": 20,
        "色": "#98df8a",
        "公式設備・備考": "万能工具研削盤 (計15台)",
    },
    {
        "工程順序": 8,
        "工程名": "8. 刃先処理(ホーニング)",
        "区分": "社内",
        "設備台数": 3,
        "リードタイム(日)": 0.0,
        "本あたり時間(分)": 5,
        "色": "#d62728",
        "公式設備・備考": "エアロラップ等 (計3台)",
    },
    {
        "工程順序": 9,
        "工程名": "9. 表面処理(社外コーティング)",
        "区分": "社外",
        "設備台数": 99,
        "リードタイム(日)": 14.0,
        "本あたり時間(分)": 0,
        "色": "#ff7f0e",
        "公式設備・備考": "外部コーティング業者 (14日)",
    },
    {
        "工程順序": 10,
        "工程名": "10. 後処理",
        "区分": "社内",
        "設備台数": 5,
        "リードタイム(日)": 0.0,
        "本あたり時間(分)": 5,
        "色": "#ffbb78",
        "公式設備・備考": "洗浄・バリ取り (計5台)",
    },
    {
        "工程順序": 11,
        "工程名": "11. レーザーマーキング",
        "区分": "社内",
        "設備台数": 2,
        "リードタイム(日)": 0.0,
        "本あたり時間(分)": 3,
        "色": "#9467bd",
        "公式設備・備考": "レーザー刻印機 (計2台)",
    },
    {
        "工程順序": 12,
        "工程名": "12. 出荷前最終検査",
        "区分": "社内",
        "設備台数": 5,
        "リードタイム(日)": 0.0,
        "本あたり時間(分)": 10,
        "色": "#bcbd22",
        "公式設備・備考": "KEYENCE測定器等 (計5台)",
    },
]

if "master_df" not in st.session_state:
  st.session_state.master_df = pd.DataFrame(default_process_master)

# --- 3. 進行中100ロットの自動生成 ---
if "orders_data" not in st.session_state:
  random.seed(42)
  tool_types = ["ドリル", "エンドミル", "リーマ", "Tスロットカッター"]
  base_date = datetime.date(2026, 9, 15)

  generated_orders = []
  for i in range(1, 101):
    m_no = f"M{i:03d}"
    dwg = f"DWG-{random.randint(100, 999)}"
    t_type = random.choice(tool_types)
    size = f"ø{random.choice([3, 5, 6, 8, 10, 12, 16, 20])}"
    qty = random.choice([5, 10, 20, 30, 50, 100, 150, 200, 300, 500])

    ord_date = base_date + datetime.timedelta(days=random.randint(0, 30))
    req_date = ord_date + datetime.timedelta(days=random.randint(25, 50))
    ans_date = req_date
    buffer_d = 3
    re_ans_date = req_date - datetime.timedelta(days=buffer_d)

    generated_orders.append({
        "製造番号": m_no,
        "図面番号": dwg,
        "工具の種類": t_type,
        "サイズ": size,
        "仕掛け本数": qty,
        "受注日": ord_date.strftime("%Y-%m-%d"),
        "希望納期": req_date.strftime("%Y-%m-%d"),
        "回答納期": ans_date.strftime("%Y-%m-%d"),
        "再回答納期(合意)": re_ans_date.strftime("%Y-%m-%d"),
        "バッファ(日)": buffer_d,
        "優先順位": 2,
        "ステータス": "進行中",
        "督促の有無": "なし",
    })
  st.session_state.orders_data = generated_orders

# --- 共通計算エンジン ---
work_sat = st.sidebar.checkbox("土曜日を臨時稼働日に設定", value=False)
st.sidebar.divider()

all_orders_df = pd.DataFrame(st.session_state.orders_data)
active_orders_df = all_orders_df[all_orders_df["ステータス"] != "完了"].copy()
active_orders_df = active_orders_df.sort_values(
    by=["優先順位", "受注日", "希望納期"]
)
master_df = st.session_state.master_df.sort_values(by="工程順序")

now = datetime.datetime(2026, 9, 15, 8, 0, 0)
machine_schedules = {}
for _, proc in master_df.iterrows():
  val = proc["設備台数"]
  m_count = 99 if (pd.isna(val) or proc["区分"] == "社外") else max(1, int(val))
  machine_schedules[proc["工程順序"]] = [now] * m_count

gantt_elements = []
summary_rows = []
process_workload = {p_name: 0.0 for p_name in master_df["工程名"]}
process_capacities = {}

for _, proc in master_df.iterrows():
  if proc["区分"] == "社内":
    process_capacities[proc["工程名"]] = proc["設備台数"] * 20.0 * 8.0
  else:
    process_capacities[proc["工程名"]] = 999.0

for _, order in active_orders_df.iterrows():
  m_no = order["製造番号"]
  qty = order["仕掛け本数"]
  order_date_dt = datetime.datetime.strptime(order["受注日"], "%Y-%m-%d").replace(
      hour=8, minute=0, second=0
  )
  lot_current_time = order_date_dt

  for _, proc in master_df.iterrows():
    p_seq = proc["工程順序"]
    p_name = proc["工程名"]
    p_type = proc["区分"]
    lt_days = (
        float(proc["リードタイム(日)"]) if pd.notna(proc["リードタイム(日)"]) else 0.0
    )
    proc_min = (
        float(proc["本あたり時間(分)"])
        if pd.notna(proc["本あたり時間(分)"])
        else 0.0
    )
    color_code = proc["色"] if pd.notna(proc["色"]) else "#1f77b4"

    units = machine_schedules[p_seq]
    earliest_unit_idx = units.index(min(units))
    machine_available_time = units[earliest_unit_idx]

    start_t = max(lot_current_time, machine_available_time)

    wait_hours = (start_t - lot_current_time).total_seconds() / 3600.0
    if wait_hours > 0.05:
      gantt_elements.append({
          "製造番号": m_no,
          "工程・要素": f"{p_name} (設備待ち)",
          "開始日時": lot_current_time,
          "終了日時": start_t,
          "タイプ": "待ち時間",
          "色": "#d3d3d3",
          "詳細": f"【設備待ち】着手可能: {start_t.strftime('%m-%d %H:%M')}",
      })

    if p_type == "社外":
      end_t = start_t + datetime.timedelta(days=lt_days)
      job_hours = lt_days * 8.0
    else:
      total_proc_hours = (qty * proc_min) / 60.0
      end_t = add_working_hours(
          start_t, total_proc_hours, work_saturday=work_sat
      )
      job_hours = total_proc_hours

    process_workload[p_name] += job_hours

    machine_schedules[p_seq][earliest_unit_idx] = end_t
    lot_current_time = end_t

    gantt_elements.append({
        "製造番号": m_no,
        "工程・要素": p_name,
        "開始日時": start_t,
        "終了日時": end_t,
        "タイプ": "実加工",
        "色": color_code,
        "詳細": f"【実加工】{p_name} ({qty}本) 完了: {end_t.strftime('%m-%d %H:%M')}",
    })

  re_ans_date = pd.to_datetime(order["再回答納期(合意)"])
  is_delayed = lot_current_time > re_ans_date
  delay_hours = (lot_current_time - re_ans_date).total_seconds() / 3600.0
  status = (
      f"⚠️再回答納期遅延 (+{delay_hours/24.0:.1f}日)"
      if is_delayed
      else "OK (再回答内)"
  )

  summary_rows.append({
      "製造番号": m_no,
      "受注日": order["受注日"],
      "希望納期": order["希望納期"],
      "回答納期": order["回答納期"],
      "再回答納期(合意)": order["再回答納期(合意)"],
      "工具の種類": order["工具の種類"],
      "仕掛け本数": qty,
      "バッファ(日)": order["バッファ(日)"],
      "即答・完成予定日時": lot_current_time.strftime("%Y-%m-%d %H:%M"),
      "判定ステータス": status,
      "遅延フラグ": is_delayed,
      "遅延時間(日)": max(0.0, round(delay_hours / 24.0, 1)),
      "完了dt": lot_current_time,
  })

df_gantt_elem = pd.DataFrame(gantt_elements)
df_summary = pd.DataFrame(summary_rows)

sorted_workload = sorted(process_workload.items(), key=lambda x: x[1], reverse=True)
top5_bottlenecks = sorted_workload[:5]
df_summary_sorted = df_summary.sort_values(by="完了dt")

# ==========================================
# メイン画面：3つの視点（タブ切り替え）
# ==========================================
view_sales, view_prod, view_boss, view_admin = st.tabs([
    "👨‍💼 【営業の視点】 新規受注入力・再回答管理",
    "🏭 【生産管理の視点】 ネックTop5・納期調整・全注文一覧",
    "👔 【社長の視点】 経営ダッシュボード・工場余裕度・全100ロット",
    "⚙️ データ・マスター管理",
])

# ------------------------------------------
# 1. 営業の視点
# ------------------------------------------
with view_sales:
  st.subheader("➕ 新規受注のインプット（受注日・回答・再回答納期の設定）")
  with st.form("new_order_sales_form"):
    c1, c2, c3 = st.columns(3)
    with c1:
      new_mno = st.text_input(
          "製造番号", value=f"M{len(st.session_state.orders_data)+1:03d}"
      )
      new_tool = st.selectbox(
          "工具の種類", ["エンドミル", "ドリル", "リーマ", "Tスロットカッター"]
      )
      new_size = st.text_input("サイズ", value="ø10.0")
    with c2:
      new_qty = st.number_input("仕掛け本数 (5〜500)", min_value=5, max_value=500, value=100)
      new_ord_date = st.date_input("受注日", value=datetime.date(2026, 10, 1))
      new_req_date = st.date_input(
          "顧客希望納期", value=datetime.date(2026, 11, 20)
      )
    with c3:
      new_ans_date = st.date_input(
          "初回回答納期", value=datetime.date(2026, 11, 20)
      )
      new_buffer = st.number_input(
          "安全バッファ(日)", min_value=0, max_value=10, value=3
      )
      new_prio = st.radio("注文区分", ["通常", "★特急割り込み最優先"])

    submitted = st.form_submit_button("📥 受注データをインプットして計算する")
    if submitted:
      prio_val = 1 if new_prio == "★特急割り込み最優先" else 2
      re_ans = new_req_date - datetime.timedelta(days=int(new_buffer))
      st.session_state.orders_data.append({
          "製造番号": new_mno,
          "図面番号": "DWG-NEW",
          "工具の種類": new_tool,
          "サイズ": new_size,
          "仕掛け本数": new_qty,
          "受注日": new_ord_date.strftime("%Y-%m-%d"),
          "希望納期": new_req_date.strftime("%Y-%m-%d"),
          "回答納期": new_ans_date.strftime("%Y-%m-%d"),
          "再回答納期(合意)": re_ans.strftime("%Y-%m-%d"),
          "バッファ(日)": new_buffer,
          "優先順位": prio_val,
          "ステータス": "進行中",
          "督促の有無": "★特急" if prio_val == 1 else "なし",
      })
      st.success(f"製造番号 {new_mno} をインプットしました！")
      st.rerun()

  st.divider()
  st.subheader("✨ 直近で完成する注文（お客様への出荷・連絡用）")
  st.dataframe(
      df_summary_sorted[[
          "製造番号",
          "受注日",
          "希望納期",
          "回答納期",
          "再回答納期(合意)",
          "工具の種類",
          "仕掛け本数",
          "即答・完成予定日時",
          "判定ステータス",
      ]].head(10),
      use_container_width=True,
  )

# ------------------------------------------
# 2. 生産管理の視点（ネックTop5 ＋ 個別調整 ＋ 全注文一覧）
# ------------------------------------------
with view_prod:
  st.subheader("🏭 生産管理課用：ネックTop5分析 & 個別納期調整")
  col_n1, col_n2, col_n3, col_n4, col_n5 = st.columns(5)
  top5_cols = [col_n1, col_n2, col_n3, col_n4, col_n5]
  for i, (p_name, hrs) in enumerate(top5_bottlenecks):
    top5_cols[i].metric(
        label=f"第 {i+1} 位",
        value=p_name.split(". ")[1] if ". " in p_name else p_name,
        delta=f"{hrs/8.0:.1f}日分",
        delta_color="inverse",
    )

  st.divider()
  st.subheader("🛠️ 特定注文の納期調整（再回答納期の変更・上書き）")
  with st.form("reschedule_form"):
    target_mno = st.selectbox(
        "調整対象の製造番号を選択", active_orders_df["製造番号"].tolist()
    )
    new_re_date = st.date_input(
        "新しい再回答納期（合意納期）を指定", value=datetime.date(2026, 11, 25)
    )
    res_submit = st.form_submit_button("🔄 この注文の再回答納期を更新する")
    if res_submit:
      for ord_item in st.session_state.orders_data:
        if ord_item["製造番号"] == target_mno:
          ord_item["再回答納期(合意)"] = new_re_date.strftime("%Y-%m-%d")
      st.success(f"製造番号 {target_mno} の再回答納期を更新しました！")
      st.rerun()

  st.divider()
  st.subheader("💡 波及を最小限にするための【変更・リスケ候補 5選】レコメンド")
  recommend_df = active_orders_df.copy()
  recommend_df["スコア"] = recommend_df["仕掛け本数"] * 0.1
  rec_top5 = recommend_df.sort_values(by="スコア").head(5)

  rec_display = []
  for _, r_row in rec_top5.iterrows():
    rec_display.append({
        "推奨製造番号": r_row["製造番号"],
        "工具": r_row["工具の種類"],
        "本数": f"{r_row['仕掛け本数']}本",
        "現・再回答納期": r_row["再回答納期(合意)"],
        "推奨対応": "納期を3日後ろにずらす",
        "理由": "小ロットかつ他の注文への影響が最小限であるため",
    })
  st.table(pd.DataFrame(rec_display))

  st.divider()
  st.subheader("📋 進行中100ロット 全注文・納期一覧（生産管理確認用）")
  st.info("すべての進行中注文の進捗、合意納期、完成予定日を一覧で管理できます。")
  st.dataframe(
      df_summary[[
          "製造番号",
          "受注日",
          "希望納期",
          "回答納期",
          "再回答納期(合意)",
          "工具の種類",
          "仕掛け本数",
          "バッファ(日)",
          "即答・完成予定日時",
          "判定ステータス",
      ]],
      use_container_width=True,
  )

# ------------------------------------------
# 3. 社長の視点
# ------------------------------------------
with view_boss:
  st.subheader("👔 社長用：経営ダッシュボード & 工場全体の空きキャパシティ")

  total_load = sum(
      hrs
      for p_name, hrs in process_workload.items()
      if "社外" not in p_name
  )
  total_capa = sum(
      cap
      for p_name, cap in process_capacities.items()
      if "社外" not in p_name
  )
  overall_usage = min(100.0, (total_load / total_capa) * 100.0)
  remaining_capacity_qty = int(15000 * (1.0 - overall_usage / 100.0))

  kc1, kc2, kc3, kc4 = st.columns(4)
  kc1.metric("工場全体キャパ使用率", f"{overall_usage:.1f} %")
  kc2.metric(
      "追加受入可能枠 (残余能力)",
      f"約 {remaining_capacity_qty:,} 本",
      delta="受注可能" if remaining_capacity_qty > 1000 else "満杯近し",
  )
  kc3.metric("進行中総ロット数", f"{len(df_summary)} 件")
  delayed_count = len(df_summary[df_summary["遅延フラグ"] == True])
  kc4.metric(
      "納期遅延リスク件数",
      f"{delayed_count} 件",
      delta="要対策" if delayed_count > 0 else "正常",
      delta_color="inverse",
  )

  st.divider()
  st.subheader("📊 工程別の設備余裕度（各工程の稼働率と残余枠）")
  proc_capacity_list = []
  for _, p_row in master_df[master_df["区分"] == "社内"].iterrows():
    p_name = p_row["工程名"]
    used = process_workload[p_name]
    capa = process_capacities[p_name]
    rate = min(100.0, (used / capa) * 100.0)
    proc_capacity_list.append({
        "工程名": p_name.split(". ")[1] if ". " in p_name else p_name,
        "使用率(%)": round(rate, 1),
        "空き容量(%)": round(max(0.0, 100.0 - rate), 1),
    })

  df_capa_chart = pd.DataFrame(proc_capacity_list)
  fig_capa = px.bar(
      df_capa_chart,
      x=["使用率(%)", "空き容量(%)"],
      y="工程名",
      orientation="h",
      title="工程別キャパシティ使用率 vs 空き枠 (%)",
      color_discrete_map={"使用率(%)": "#2ca02c", "空き容量(%)": "#e0e0e0"},
      height=350,
  )
  st.plotly_chart(fig_capa, use_container_width=True)

  st.divider()
  st.subheader("📈 工場全体 タイムライン（全100ロット表示・縦スクロール）")
  if not df_gantt_elem.empty:
    chart_height = max(600, len(active_orders_df) * 22)
    fig = px.timeline(
        df_gantt_elem,
        x_start="開始日時",
        x_end="終了日時",
        y="製造番号",
        color="工程・要素",
        height=chart_height,
    )
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------
# 4. データ・マスター管理
# ------------------------------------------
view_admin.subheader(
    "⚙️ 公式設備データ付き工程マスター & 全データ一括編集"
)
edited_all = view_admin.data_editor(
    pd.DataFrame(st.session_state.orders_data), use_container_width=True
)
if view_admin.button("一括データを保存・更新"):
  st.session_state.orders_data = edited_all.to_dict("records")
  st.success("最新のデータを保存しました。")
  st.rerun()

view_admin.divider()
view_admin.subheader("📋 公式設備データ・工程マスター設定")
edited_master = view_admin.data_editor(
    st.session_state.master_df, num_rows="fixed", use_container_width=True
)
if view_admin.button("マスターを保存"):
  st.session_state.master_df = edited_master
  st.success("マスターを保存しました。")
  st.rerun()