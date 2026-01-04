import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(layout="wide")

# ==========================================
# ⚙️ โซนตั้งค่า (เปลี่ยนชื่อบอสตรงนี้)
# ==========================================
BOSS_CONFIG = [
    {"name": "แทโอ", "color": "#ffcccc"},   # สีแดงอ่อน
    {"name": "ไคล์", "color": "#cce5ff"}, # สีฟ้าอ่อน
    {"name": "ยอนฮี", "color": "#ccffcc"},    # สีเขียวอ่อน
    {"name": "คาร์ม่า", "color": "#e5ccff"}    # สีม่วงอ่อน
]
# ==========================================

st.title("⚔️ Guild Boss Damage Calculator")

# --- 1. เชื่อมต่อ ---
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df_source = conn.read(worksheet="Members", ttl=0)
    name_col = df_source.columns[0]
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

# --- 2. เตรียมข้อมูล ---
if 'df_input' not in st.session_state:
    working_df = df_source.copy()
    for i, boss in enumerate(BOSS_CONFIG, start=1):
        if f"Boss {i} Dmg" not in working_df.columns: working_df[f"Boss {i} Dmg"] = 0
        if f"Boss {i} Hits" not in working_df.columns: working_df[f"Boss {i} Hits"] = 0
    st.session_state.df_input = working_df.fillna(0)

# --- 3. ตั้งค่าการแสดงผล (เปลี่ยนตรงนี้!) ---
column_config = {
    name_col: st.column_config.TextColumn("ชื่อสมาชิก", disabled=True),
}

# สร้างตัวเลือก 0-14 เตรียมไว้
hit_options = [i for i in range(15)] # [0, 1, 2, ..., 14]

for i, boss in enumerate(BOSS_CONFIG, start=1):
    # ช่องดาเมจ
    column_config[f"Boss {i} Dmg"] = st.column_config.NumberColumn(
        f"{boss['name']} (Dmg)", 
        min_value=0,
        format="%d" 
    )
    
    # [เปลี่ยนใหม่] ช่องจำนวนรอบ -> ใช้ SelectboxColumn (Dropdown)
    column_config[f"Boss {i} Hits"] = st.column_config.SelectboxColumn(
        f"รอบ (0-14)",
        options=hit_options, # ใส่ตัวเลือก 0-14
        required=True,       # บังคับเลือก ห้ามปล่อยว่าง
        help=f"เลือกจำนวนรอบของ {boss['name']}",
        width="small"        # ปรับความกว้างให้พอดี
    )

# --- 4. แสดงตาราง Data Editor ---
st.info("💡 เลือกจำนวนรอบจาก List (0-14) และกรอกดาเมจ")

# ใช้แยกแท็บเหมือนเดิมเพื่อให้กรอกง่าย
tabs = st.tabs([b['name'] for b in BOSS_CONFIG])

for i, (tab, boss) in enumerate(zip(tabs, BOSS_CONFIG), start=1):
    with tab:
        cols_to_show = [name_col, f"Boss {i} Hits", f"Boss {i} Dmg"]
        
        # สร้าง Config เฉพาะหน้า
        temp_config = {
            name_col: st.column_config.TextColumn("ชื่อสมาชิก", disabled=True),
            f"Boss {i} Dmg": column_config[f"Boss {i} Dmg"],
            f"Boss {i} Hits": column_config[f"Boss {i} Hits"] # ดึง Config Dropdown มาใช้
        }

        edited_subset = st.data_editor(
            st.session_state.df_input[cols_to_show],
            column_config=temp_config,
            use_container_width=True,
            hide_index=True,
            key=f"editor_boss_{i}",
            height=(len(st.session_state.df_input) * 35) + 38
        )
        
        st.session_state.df_input.update(edited_subset)

# --- 5. ปุ่มบันทึกและสรุปผล ---
st.divider()
if st.button("💾 บันทึกทั้งหมดลง Google Sheet", type="primary"):
    try:
        conn.update(worksheet="Members", data=st.session_state.df_input)
        st.toast("บันทึกเรียบร้อย!", icon="✅")
    except Exception as e:
        st.error(f"บันทึกไม่สำเร็จ: {e}")

# --- ตารางสรุปผล ---
st.subheader("🏆 สรุปผลรวม (Overview)")
result_df = st.session_state.df_input[[name_col]].copy()
all_hits_cols = []

for i, boss in enumerate(BOSS_CONFIG, start=1):
    dmg_col = f"Boss {i} Dmg"
    hits_col = f"Boss {i} Hits"
    avg_col = f"{boss['name']} (Avg)"
    all_hits_cols.append(hits_col)
    
    result_df[avg_col] = st.session_state.df_input.apply(
        lambda row: row[dmg_col] / row[hits_col] if row[hits_col] > 0 else 0, axis=1
    )

result_df["Total Hits"] = st.session_state.df_input[all_hits_cols].sum(axis=1)

# ฟังก์ชันใส่สี
def highlight_boss_columns(df):
    styles = pd.DataFrame('', index=df.index, columns=df.columns)
    for col in df.columns:
        for boss in BOSS_CONFIG:
            if boss['name'] in col:
                styles[col] = f'background-color: {boss["color"]}; color: black;'
        if "Total Hits" in col:
            styles[col] = 'background-color: #ffffcc; font-weight: bold;'
    return styles

st.dataframe(
    result_df.style
    .apply(highlight_boss_columns, axis=None)
    .format("{:.2f}", subset=[f"{b['name']} (Avg)" for b in BOSS_CONFIG])
    .format("{:.0f}", subset=["Total Hits"]),
    use_container_width=True,
    hide_index=True
)