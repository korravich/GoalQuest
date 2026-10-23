"""Korvian: เนื้อหาของแต่ละหน้า (สรุปผล, Money Line, Health Line, Study Line) และกราฟ"""
import random
from datetime import timedelta

import altair as alt
import pandas as pd
import streamlit as st

import db


# ==========================================
# กราฟ
# ==========================================

def show_bar_chart(df, monthly=False, goal=0.0, goal_name=""):
    """แท่งรายรับ/รายจ่าย + เส้นเงินเก็บ + เส้นเป้าหมาย ใช้แกนตัวเลขเดียวกัน"""
    data = df.reset_index()
    time_col = data.columns[0]
    data["label"] = data[time_col].dt.strftime("%m/%Y" if monthly else "%d/%m")
    order = list(dict.fromkeys(data["label"]))

    bars_data = data.melt(
        id_vars=[time_col, "label"],
        value_vars=["รายรับ", "รายจ่าย"],
        var_name="ประเภท",
        value_name="จำนวนเงิน"
    )

    has_balance = "เงินเก็บ" in data.columns

    # หาช่วงแกนเดียวที่ครอบคลุมทุกอย่าง เผื่อที่ว่างด้านบน 20%
    tops = [float(bars_data["จำนวนเงิน"].max())]
    lows = [0.0]
    if has_balance:
        tops.append(float(data["เงินเก็บ"].max()))
        lows.append(float(data["เงินเก็บ"].min()))
    if goal > 0:
        tops.append(float(goal))
    top, low = max(tops), min(lows)
    span = top - low
    y_max = top + span * 0.2 if span > 0 else 100
    y_scale = alt.Scale(domain=[low, y_max])

    x_enc = alt.X(
        "label:N", sort=order, title=None,
        axis=alt.Axis(labelAngle=-45)
    )

    bars = (
        alt.Chart(bars_data)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            x=x_enc,
            xOffset=alt.XOffset("ประเภท:N", sort=["รายรับ", "รายจ่าย"]),
            y=alt.Y("จำนวนเงิน:Q", title="บาท", scale=y_scale),
            color=alt.Color(
                "ประเภท:N",
                scale=alt.Scale(
                    domain=["รายรับ", "รายจ่าย"],
                    range=["#2ECC71", "#E74C3C"]
                ),
                legend=alt.Legend(title=None, orient="top")
            ),
            tooltip=["label", "ประเภท", "จำนวนเงิน"]
        )
    )

    layers = [bars]

    if has_balance:
        line = (
            alt.Chart(data)
            .mark_line(
                color="#3498DB", strokeWidth=3,
                point=alt.OverlayMarkDef(color="#3498DB", size=60)
            )
            .encode(
                x=x_enc,
                y=alt.Y("เงินเก็บ:Q", title="บาท", scale=y_scale),
                tooltip=[
                    alt.Tooltip("label:N", title="ช่วง"),
                    alt.Tooltip("เงินเก็บ:Q", title="เงินเก็บ", format=",.2f")
                ]
            )
        )
        layers.append(line)

    if goal > 0:
        rule = (
            alt.Chart(pd.DataFrame({"เป้าหมาย": [float(goal)]}))
            .mark_rule(color="#F39C12", strokeWidth=1.5, strokeDash=[6, 4])
            .encode(
                y=alt.Y("เป้าหมาย:Q", title="บาท", scale=y_scale),
                tooltip=[alt.Tooltip("เป้าหมาย:Q", format=",.2f")]
            )
        )
        layers.append(rule)

    chart = alt.layer(*layers).properties(height=380, width=520)
    st.altair_chart(chart, use_container_width=False)

    if has_balance:
        text = "🔵 เส้นฟ้า = เงินเก็บ"
        if goal > 0:
            text += (
                f"   ·  🟠 เส้นประ = เป้าหมาย {goal_name} {goal:,.2f} บาท "
                "(เส้นฟ้าแตะเส้นนี้ = ถึงเป้าแล้ว)"
            )
        st.caption(text)


# ==========================================
# หน้า: สรุปผล
# ==========================================

def _goal_message(name, far):
    """สุ่มข้อความให้กำลังใจตามความคืบหน้า (far = เงินที่ยังขาดถึงเป้า)"""
    if far > 0:
        messages = [
            f"คุณยังขาดเงินอีก {far:,.2f} บาทนะ แล้ว **{name}** ที่คุณอยากได้ล่ะ?",
            f"ขาดอีกแค่ {far:,.2f} บาทเองงงง อีกนิดเดียวก็ได้แล้ว 🤏🤏",
            f"เอ้าท่องพร้อมกันนน เพื่อ **{name}** เพื่อ **{name}** เพื่อ **{name}** 😀",
            "อย่าเพิ่งยอมแพ้ ความสำเร็จมันต้องใช้เวลานะ! 👊",
            "วันนี้อาจยังไม่ถึง แต่คุณต้องทำได้แน่!",
            f"ลำบากตอนนี้ เดี๋ยวตอนได้ **{name}** ก็สบายแล้ววว 😣😣",
        ]
    elif far == 0:
        messages = [
            f"เย้!! คุณสามารถซื้อ **{name}** ได้แล้ว 🎉🎉",
            "ยินดีด้วยยยย คุณทำสำเร็จแล้ว!",
            "ได้แล้วววว นี่แหละชัยชนะ ฮ่าฮ่าฮ่า",
            f"เห็นมั้ยล่ะ **{name}** อยู่ใกล้แค่เอื้อมเท่านั้นแหละ",
            "สบายมาก 💪💪",
            "ได้เวลาสำหรับของชิ้นต่อไปแล้ว 🤩🤩",
        ]
    else:
        over = -far
        messages = [
            f"ตอนนี้คุณสามารถซื้อ **{name}** ได้เป็นร้อยอันแล้วม้าง",
            "คุณนี่อัจฉริยะด้านการเก็บเงินชัดๆ!!",
            f"ทำได้แล้วว และยังมีเงินเกินมาอีกตั้ง {over:,.2f} บาทแหละ",
            f"เห็นมั้ยล่ะ **{name}** อยู่ใกล้แค่เอื้อมเท่านั้นแหละ",
            "สบายมาก 💪💪",
            "คุณมีเงินเกินแล้ว ซื้อได้ทั้งบริษัทแล้วมั้งเนี่ย 💰",
            "อนาคตเศรษฐีพันล้านรึป่าวเนี่ยย 💸💸",
        ]
    return random.choice(messages)


def _chart_section():
    st.write("---")
    st.subheader("📊 รายรับ-รายจ่าย")

    period = st.radio(
        "ช่วงเวลา",
        ["7 วัน", "30 วัน", "รายเดือน"],
        horizontal=True,
        label_visibility="collapsed"
    )

    try:
        uid = st.session_state["user_id"]
        balance = st.session_state.balance
        goal = st.session_state.goal
        goal_name = st.session_state.item_name

        if period == "รายเดือน":
            df = db.load_monthly(uid)
            if df.empty:
                st.info(
                    "ยังไม่มีสรุปรายเดือน "
                    "ข้อมูลจะถูกรวมเป็นรายเดือนเมื่อเก่ากว่า 30 วัน"
                )
            else:
                chart_df = db.add_balance_monthly(uid, df, balance)
                show_bar_chart(chart_df, monthly=True, goal=goal, goal_name=goal_name)

                table = df.copy()
                table.index = table.index.strftime("%m/%Y")
                table["คงเหลือ"] = table["รายรับ"] - table["รายจ่าย"]
                st.dataframe(table, use_container_width=True)
        else:
            days = 7 if period == "7 วัน" else 30
            df = db.load_daily_range(uid, days)

            total_in = df["รายรับ"].sum()
            total_out = df["รายจ่าย"].sum()

            c1, c2, c3 = st.columns(3)
            c1.metric("รายรับรวม", f"{total_in:,.2f}")
            c2.metric("รายจ่ายรวม", f"{total_out:,.2f}")
            c3.metric("สุทธิ", f"{total_in - total_out:,.2f}")

            if total_in == 0 and total_out == 0:
                st.info(f"ใน {days} วันที่ผ่านมายังไม่มีการบันทึก")
            else:
                chart_df = db.add_balance_daily(df, balance)
                show_bar_chart(chart_df, goal=goal, goal_name=goal_name)

    except Exception as e:
        st.error(f"โหลดกราฟไม่สำเร็จ: {e}")


def summary_page():
    st.subheader("🏆 สรุปเป้าหมาย")
    st.write("ยินดีต้อนรับ นี่คือภาพรวมในตอนนี้")

    ss = st.session_state
    st.metric(label="เงินเก็บปัจจุบันของคุณ", value=f"{ss.balance:,.2f} บาท")
    st.text(f"🎯 Goal : {ss.item_name} ราคา {ss.goal:,.2f} บาท")

    if ss.goal > 0:
        st.info(_goal_message(ss.item_name, ss.goal - ss.balance))

    _chart_section()


# ==========================================
# หน้า: Money Line
# ==========================================

def money_page():
    st.subheader("💰 Money Line: วางแผนการเงินเพื่อเป้าหมาย")

    ss = st.session_state
    sb = db.user_client()
    uid = ss["user_id"]

    # ----- เป้าหมาย -----
    item = st.text_input(
        "คุณกำลังเก็บเงินไปเพื่อซื้ออะไร? (เช่น หูฟัง, เกม):",
        value=ss.item_name
    )
    target_goal = st.number_input(
        "ของชิ้นนั้นราคากี่บาท?:",
        min_value=0.0,
        value=ss.goal,
        step=100.0
    )

    if st.button("บันทึกเป้าหมายการซื้อของ"):
        try:
            sb.table("player_data").update({
                "item": item,
                "goal": str(target_goal)
            }).eq("user_id", uid).execute()

            ss.item_name = item
            ss.goal = target_goal
            st.success("บันทึกข้อมูลเป้าหมายใหม่เรียบร้อยแล้ว!")

        except Exception as e:
            st.error(f"บันทึกเป้าหมายไม่สำเร็จ: {e}")

    # ----- รายรับ-รายจ่าย -----
    st.write("---")
    st.write("### บันทึกรายรับ-รายจ่าย")

    today = db.today_th()
    record_date = st.date_input(
        "วันที่",
        value=today,
        min_value=today - timedelta(days=30),
        max_value=today
    )
    income = st.number_input("ได้เงินกี่บาท💰:", min_value=0.0, value=0.0)
    expense = st.number_input("ใช้จ่ายกี่บาท💸:", min_value=0.0, value=0.0)

    if st.button("คำนวณและบันทึกยอดเงิน"):
        if income == 0 and expense == 0:
            st.warning("กรุณากรอกรายรับหรือรายจ่ายอย่างน้อยหนึ่งช่อง")
        else:
            try:
                # 1) บันทึกลง daily_records (ถ้ามีวันนั้นอยู่แล้วให้บวกทบ)
                existing = (
                    sb.table("daily_records")
                    .select("income, expense")
                    .eq("user_id", uid)
                    .eq("record_date", record_date.isoformat())
                    .execute()
                )
                old_income = float(existing.data[0]["income"]) if existing.data else 0.0
                old_expense = float(existing.data[0]["expense"]) if existing.data else 0.0

                sb.table("daily_records").upsert({
                    "user_id": uid,
                    "record_date": record_date.isoformat(),
                    "income": old_income + income,
                    "expense": old_expense + expense
                }).execute()

                # 2) อัปเดตยอดเงินเก็บปัจจุบัน
                new_balance = ss.balance + income - expense
                sb.table("player_data").update({
                    "balance": new_balance
                }).eq("user_id", uid).execute()

                ss.balance = new_balance
                st.success(
                    "บันทึกเรียบร้อยแล้ว! "
                    "ลองกลับไปดูหน้าแรกเพื่อเช็กยอดเงิน"
                )

            except Exception as e:
                st.error(f"บันทึกยอดเงินไม่สำเร็จ: {e}")

    # ----- ล้างเงินเก็บ -----
    st.write("---")
    st.subheader("🧹 จัดการเงินเก็บ")

    if st.button("ล้างเงินเก็บ", key="reset_balance"):
        ss["show_reset_balance_confirm"] = True

    if ss.get("show_reset_balance_confirm", False):
        st.warning(
            "⚠️ คุณกำลังจะตั้งยอดเงินเก็บเป็น 0 บาท และล้างประวัติรายรับ-รายจ่าย "
            "(รวมกราฟ) ทั้งหมด การดำเนินการนี้ไม่สามารถย้อนกลับได้ "
            "แต่ชื่อเป้าหมายและราคาเป้าหมายจะไม่ถูกลบ"
        )

        confirm_col, cancel_col = st.columns(2)

        with confirm_col:
            if st.button("ยืนยันล้างเงินเก็บ", key="btn_confirm_reset_balance"):
                try:
                    # ล้างประวัติก่อน เพื่อให้เส้นเงินเก็บเริ่มนับใหม่จาก 0
                    db.clear_history(uid)
                    sb.table("player_data").update({
                        "balance": 0
                    }).eq("user_id", uid).execute()

                    ss.balance = 0.0
                    ss["show_reset_balance_confirm"] = False
                    st.success("ล้างเงินเก็บเรียบร้อยแล้ว!")
                    st.rerun()

                except Exception as e:
                    st.error(f"ล้างเงินเก็บไม่สำเร็จ: {e}")

        with cancel_col:
            if st.button("ยกเลิก", key="btn_cancel_reset_balance"):
                ss["show_reset_balance_confirm"] = False
                st.rerun()

    st.caption(
        "หมายเหตุ: ปุ่มนี้จะล้างยอดเงินเก็บและประวัติรายรับ-รายจ่ายของบัญชีที่เข้าสู่ระบบ "
        "ไม่ลบชื่อสิ่งของหรือราคาเป้าหมาย"
    )


# ==========================================
# หน้า: Health Line
# ==========================================

# ทุก key ที่หน้า Health ใช้เก็บสถานะ (ช่องติ๊ก + ข้อความสุ่ม)
# ใช้ล้างทิ้งเมื่อเจ้าของข้อมูลเปลี่ยน เพื่อไม่ให้ข้อมูลของผู้ใช้คนก่อนค้างอยู่
HEALTH_KEYS = (
    [f"water_{i}" for i in range(1, 9)]
    + ["meal_breakfast", "meal_lunch", "meal_dinner",
       "time_breakfast", "time_lunch", "time_dinner",
       "sleep_enough", "sleep_schedule", "sleep_screen",
       "move_walk", "move_stretch", "move_activity",
       "mind_relax", "mind_enjoy", "mind_connect",
       "previous_water_count", "previous_meal_count",
       "water_tip", "meal_tip", "time_tip",
       "sleep_tip", "move_tip", "mind_tip"]
)

WATER_TIPS = [
    "พักแล้วจิบน้ำสักหน่อยมั้ยย 💧",
    "น้ำช่วยให้ร่างกายทำงานได้ดีตามปกตินะ อย่าลืมล่ะ!",
    "ไม่ต้องรีบดื่มรวดเดียว ค่อย ๆ จิบระหว่างวันเอานะ 😉😉",
]
MEAL_TIPS = [
    "อีกมื้อเดียวก็ครบแล้วนะ",
    "อย่าลืมกินอาหารให้ครบ 5 หมู่ด้วยหล่ะ 😌",
    "อย่าลืมหาเวลากินมื้อที่เหลือนะ 😉😉",
]

# ภารกิจที่เหลือ (ติ๊กครบทุกข้อ = สำเร็จ) เพิ่มภารกิจใหม่ได้ที่นี่
SIMPLE_MISSIONS = [
    {
        "title": "⏰ ภารกิจที่ 3: วันนี้ได้พักกินข้าวเป็นเวลาหรือยัง?",
        "desc": "หาเวลาพักกินอาหาร ไม่ปล่อยให้กิจกรรมต่าง ๆ เบียดเวลามื้ออาหาร",
        "items": [
            ("จัดเวลามื้อเช้าได้เหมาะสม", "time_breakfast"),
            ("มีเวลาพักกินมื้อกลางวัน", "time_lunch"),
            ("จัดเวลามื้อเย็นได้เหมาะสม", "time_dinner"),
        ],
        "tip_key": "time_tip",
        "tips": [
            "ภารกิจในเกมรอได้ แต่ท้องร้องนี่สิไม่ยอมรอ 😂",
            "อย่าลืมพักจากการเรียนหรือเล่นเกมมากินข้าวนะ!",
            "การกินอาหารสม่ำเสมอช่วยให้จัดกิจวัตรได้ดีขึ้น 🍱",
        ],
        "success": "วันนี้จัดเวลามื้ออาหารได้ครบแล้ว! ⏰",
    },
    {
        "title": "🛌 ภารกิจที่ 4: วันนี้พักผ่อนเพียงพอหรือยัง?",
        "desc": "การนอนช่วยให้ร่างกายและสมองได้พักฟื้น",
        "items": [
            ("เมื่อคืนได้นอนเพียงพอสำหรับตัวเอง", "sleep_enough"),
            ("พยายามเข้านอนและตื่นให้เป็นเวลา", "sleep_schedule"),
            ("เตรียมตัวพักจากหน้าจอก่อนนอน", "sleep_screen"),
        ],
        "tip_key": "sleep_tip",
        "tips": [
            "ตัวละครยังต้องพักฟื้น แล้วคุณล่ะ? 😂",
            "นอนดึกทุกคืน เดี๋ยวพรุ่งนี้สมองขอโหลดช้านะ 💤",
            "วัยรุ่นส่วนใหญ่มักต้องการนอนประมาณ 8–10 ชั่วโมงต่อคืน",
            "ลองวางมือถือก่อนนอน แล้วให้สมองได้พักบ้างนะ 📱",
        ],
        "success": "ภารกิจดูแลการนอนครบแล้ว ขอให้พักผ่อนเต็มที่! 💤",
    },
    {
        "title": "🚶 ภารกิจที่ 5: วันนี้ได้ขยับร่างกายหรือยัง?",
        "desc": "ไม่จำเป็นต้องออกกำลังหนัก เริ่มจากการเคลื่อนไหวที่เหมาะกับตัวเองได้",
        "items": [
            ("🚶 เดินหรือขยับร่างกายระหว่างวัน", "move_walk"),
            ("🙆 ยืดเหยียดร่างกาย", "move_stretch"),
            ("⚽ ทำกิจกรรมที่ชอบ เช่น เล่นกีฬา", "move_activity"),
        ],
        "tip_key": "move_tip",
        "tips": [
            "อย่านั่งนิ่งจนรากงอกเหมือนต้นไม้สิ 😂",
            "ลุกมายืดเส้นสักนิด ร่างกายจะได้เปลี่ยนอิริยาบถ!",
            "การเคลื่อนไหวสม่ำเสมอดีต่อสุขภาพนะ ไม่จำเป็นต้องหักโหม 💪",
        ],
        "success": "ภารกิจขยับร่างกายครบแล้ว เยี่ยมมาก! 🚶",
    },
    {
        "title": "💚 ภารกิจที่ 6: วันนี้ได้ดูแลความรู้สึกตัวเองหรือยัง?",
        "desc": "การพักใจเป็นส่วนหนึ่งของการดูแลตัวเองเหมือนกันนะ",
        "items": [
            ("หาเวลาพักจากสิ่งที่ทำอยู่", "mind_relax"),
            ("ทำกิจกรรมที่ทำให้ตัวเองมีความสุข", "mind_enjoy"),
            ("พูดคุยกับคนที่ไว้ใจเมื่ออยากระบาย", "mind_connect"),
        ],
        "tip_key": "mind_tip",
        "tips": [
            "คุณไม่ใช่หุ่นยนต์นะ พักบ้างก็ได้ 🤖",
            "ไม่จำเป็นต้องเก่งทุกนาที แค่วันนี้ดูแลตัวเองได้ก็ดีแล้ว 💚",
            "พักใจสักนิด ไม่ใช่การแพ้ แต่เป็นการให้เวลากับตัวเอง",
        ],
        "success": "ภารกิจดูแลใจสำเร็จแล้ว อย่าลืมใจดีกับตัวเองนะ 💚",
    },
]


def _isolate_health_state():
    """ถ้าเจ้าของข้อมูลเปลี่ยน (ล็อกอินคนใหม่) ให้ล้างช่องติ๊กสุขภาพของคนเดิมทิ้ง"""
    uid = st.session_state.get("user_id")
    if st.session_state.get("_health_owner") != uid:
        for key in HEALTH_KEYS:
            st.session_state.pop(key, None)
        st.session_state["_health_owner"] = uid


def _tip(text, color):
    st.markdown(
        f"<p style='color:{color}; font-size:12px;'>💬 {text}</p>",
        unsafe_allow_html=True
    )


def _progress(done, total, unit=""):
    st.caption(f"ความคืบหน้า: {done}/{total}{unit}")
    st.progress(done / total)


def _rotating_tip(tip_key, prev_key, count, options):
    """สุ่มข้อความใหม่เมื่อจำนวนที่ติ๊กเปลี่ยน ถ้าไม่เปลี่ยนใช้ข้อความเดิม"""
    if count != st.session_state.get(prev_key, -1):
        st.session_state[tip_key] = random.choice(options)
    return st.session_state.get(tip_key, options[0])


def _simple_mission(m):
    with st.expander(m["title"]):
        st.write(m["desc"])

        done = sum(
            1 for label, key in m["items"] if st.checkbox(label, key=key)
        )
        total = len(m["items"])

        if done == total:
            st.success(m["success"])
        else:
            if m["tip_key"] not in st.session_state:
                st.session_state[m["tip_key"]] = random.choice(m["tips"])
            _tip(st.session_state[m["tip_key"]], "#e05252")

        _progress(done, total)


def health_page():
    _isolate_health_state()

    st.subheader("เช็คลิสต์ร่างกายประจำวัน")
    st.write("🌱 สุขภาพที่ดีเริ่มจากสิ่งเล็ก ๆ ที่คุณทำในทุกวัน มาเช็คไปพร้อมกันเลย !😁")

    # 1. ดื่มน้ำ
    with st.expander("💧 ภารกิจที่ 1: วันนี้ดื่มน้ำครบ 8 แก้วหรือยัง?"):
        st.write("เติมพลังให้ร่างกาย จิบน้ำให้เหมาะกับความต้องการของตัวเอง!")

        cols = st.columns(4)
        water_count = 0
        for i in range(8):
            with cols[i % 4]:
                if st.checkbox(f"แก้วที่ {i + 1}", key=f"water_{i + 1}"):
                    water_count += 1

        if water_count == 8:
            st.success("ภารกิจเช็กการดื่มน้ำครบแล้ว! เยี่ยมเลย 💧")
        elif water_count == 0:
            _tip("วันนี้คุณยังไม่ได้เช็กการดื่มน้ำเลยนะ 💧", "#E53935")
        elif water_count <= 3:
            _tip("ปากแห้งเป็นทะเลทรายแล้วมั้งเนี่ย 🏜️", "#F39C12")
        else:
            _tip(
                _rotating_tip("water_tip", "previous_water_count", water_count, WATER_TIPS),
                "#3498DB"
            )

        st.session_state["previous_water_count"] = water_count
        _progress(water_count, 8)

    # 2. กินอาหารครบ 3 มื้อ
    with st.expander("🍚 ภารกิจที่ 2: วันนี้กินอาหารครบ 3 มื้อหรือยัง?"):
        st.write("เติมพลังงานให้ร่างกายด้วยมื้ออาหารที่หลากหลาย")

        meal_count = sum([
            st.checkbox("🌅 มื้อเช้า", key="meal_breakfast"),
            st.checkbox("🌄 มื้อกลางวัน", key="meal_lunch"),
            st.checkbox("🌆 มื้อเย็น", key="meal_dinner"),
        ])

        if meal_count == 3:
            st.success("บันทึกมื้ออาหารครบทั้ง 3 มื้อแล้ว! เก่งมาก 🍚")
        elif meal_count == 0:
            _tip("วันนี้คุณยังไม่ได้กินอะไรเลยนะ 🍚", "#E53935")
        elif meal_count == 1:
            _tip("อาหารที่หลากหลายช่วยให้ร่างกายได้รับสารอาหารที่จำเป็นนะ! 💪", "#F39C12")
        else:
            _tip(
                _rotating_tip("meal_tip", "previous_meal_count", meal_count, MEAL_TIPS),
                "#3498DB"
            )

        st.session_state["previous_meal_count"] = meal_count
        _progress(meal_count, 3, " มื้อ")

    # 3-6. ภารกิจที่เหลือ
    for mission in SIMPLE_MISSIONS:
        _simple_mission(mission)

    st.write("---")
    st.caption(
        "💚 เช็กลิสต์นี้มีไว้ช่วยติดตามการดูแลตัวเอง การทำได้ครบทุกข้อเป็นเรื่องดี "
        "แต่สิ่งสำคัญคือการดูแลตัวเองอย่างเหมาะสมและสม่ำเสมอในทุก ๆ วันนะ!"
    )

    # TODO: ปุ่มนี้ยังไม่ได้บันทึกลงฐานข้อมูลจริง (งานถัดไป)
    if st.button("บันทึกคะแนนสุขภาพประจำวัน"):
        st.success("บันทึกพฤติกรรมเรียบร้อย! รักษาวินัยแบบนี้ในทุกๆ วันนะครับ")


# ==========================================
# หน้า: Study Line (ชั่วคราว)
# ==========================================

def study_page():
    st.subheader("📚 Study Line")
    st.info("หน้านี้กำลังพัฒนา เร็วๆ นี้")
