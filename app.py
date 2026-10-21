import os
import random
import streamlit as st
from supabase import create_client

# ตั้งค่าหน้าตาเว็บไซต์
st.set_page_config(
    page_title="Goal Quest",
    page_icon="⚔️",
    layout="centered"
)

# ระบบเชื่อมต่อ Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# หัวเว็บไซต์
st.title("⚔️ Goal Quest ⚔️")
st.caption("Your Future Depends on What You Do Today (beta)")
st.write("---")


# ==========================================
# ระบบสมัครสมาชิกและเข้าสู่ระบบ
# ==========================================

# คืนสถานะการเข้าสู่ระบบจาก Streamlit session
if (
    "access_token" in st.session_state
    and "refresh_token" in st.session_state
):
    try:
        supabase.auth.set_session(
            st.session_state["access_token"],
            st.session_state["refresh_token"]
        )
    except Exception:
        for key in ["access_token", "refresh_token", "user_id", "user_email"]:
            st.session_state.pop(key, None)

# ถ้ายังไม่ได้เข้าสู่ระบบ ให้แสดงหน้าสมัครและล็อกอิน
if "user_id" not in st.session_state:
    st.subheader("Start your goals")

    login_tab, signup_tab = st.tabs(
        ["เข้าสู่ระบบ", "สมัครสมาชิก"]
    )

    with login_tab:
        with st.form("login_form"):
            login_email = st.text_input("อีเมล")
            login_password = st.text_input(
                "รหัสผ่าน",
                type="password"
            )
            login_submit = st.form_submit_button(
                "เข้าสู่ระบบ",
                use_container_width=True
            )

        if login_submit:
            try:
                result = supabase.auth.sign_in_with_password({
                    "email": login_email.strip(),
                    "password": login_password
                })

                if result.user and result.session:
                    st.session_state["user_id"] = result.user.id
                    st.session_state["user_email"] = result.user.email
                    st.session_state["access_token"] = (
                        result.session.access_token
                    )
                    st.session_state["refresh_token"] = (
                        result.session.refresh_token
                    )
                    st.rerun()

            except Exception:
                st.error(
                    "เข้าสู่ระบบไม่สำเร็จ "
                    "โปรดตรวจสอบอีเมล รหัสผ่าน "
                    "หรือการยืนยันอีเมล"
                )

    with signup_tab:
        with st.form("signup_form"):
            signup_email = st.text_input("อีเมลสำหรับสมัคร")
            signup_password = st.text_input(
                "ตั้งรหัสผ่าน",
                type="password"
            )
            signup_password_again = st.text_input(
                "ยืนยันรหัสผ่าน",
                type="password"
            )
            signup_submit = st.form_submit_button(
                "สมัครสมาชิก",
                use_container_width=True
            )

        if signup_submit:
            if not signup_email.strip():
                st.error("กรุณากรอกอีเมล")
            elif len(signup_password) < 8:
                st.error("รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร")
            elif signup_password != signup_password_again:
                st.error("รหัสผ่านทั้งสองช่องไม่ตรงกัน")
            else:
                try:
                    result = supabase.auth.sign_up({
                        "email": signup_email.strip(),
                        "password": signup_password
                    })

                    if result.session and result.user:
                        st.session_state["user_id"] = result.user.id
                        st.session_state["user_email"] = (
                            result.user.email
                        )
                        st.session_state["access_token"] = (
                            result.session.access_token
                        )
                        st.session_state["refresh_token"] = (
                            result.session.refresh_token
                        )
                        st.success("สมัครสมาชิกสำเร็จ!")
                        st.rerun()
                    else:
                        st.success(
                            "ส่งคำขอสมัครแล้ว "
                            "กรุณาตรวจอีเมลเพื่อยืนยันบัญชี "
                            "ก่อนเข้าสู่ระบบ"
                        )

                except Exception as e:
                    st.error(f"สมัครสมาชิกไม่สำเร็จ: {e}")


    # ยังไม่เข้าสู่ระบบ ห้ามแสดงส่วนเกมด้านล่าง
    st.stop()

# แสดงบัญชีที่กำลังใช้งาน
st.caption(
    "บัญชีที่เข้าสู่ระบบ: "
    + str(st.session_state.get("user_email", "ผู้เล่น"))
)

if st.button("ออกจากระบบ"):
    try:
        supabase.auth.sign_out()
    except Exception:
        pass

    for key in ["access_token", "refresh_token", "user_id", "user_email"]:
        st.session_state.pop(key, None)

    st.rerun()

st.write("---")



# ==========================================
# 💾 ระบบหลังบ้าน: โหลดข้อมูลจาก Supabase
# ==========================================

if "player_data_loaded" not in st.session_state:
    try:
        user_id = st.session_state["user_id"]

        # โหลดข้อมูลของบัญชีที่เข้าสู่ระบบอยู่เท่านั้น
        response = (
            supabase.table("player_data")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )

        if response.data:
            player_data = response.data[0]
        else:
            # สร้างข้อมูลเริ่มต้นสำหรับผู้เล่นใหม่
            new_player = {
                "user_id": user_id,
                "balance": 0,
                "goal": "0",
                "item": "สิ่งที่อยากได้"
            }

            supabase.table("player_data").insert(
                new_player
            ).execute()

            player_data = new_player

        st.session_state.balance = float(
            player_data["balance"]
        )
        st.session_state.goal = float(
            player_data["goal"]
        )
        st.session_state.item_name = player_data["item"]
        st.session_state.player_data_loaded = True

    except Exception as e:
        st.error(f"โหลดข้อมูลไม่สำเร็จ: {e}")
        st.stop()


# ==========================================
# 🧭 ระบบเมนูหลัก (Sidebar ด้านข้าง)
# ==========================================

st.sidebar.markdown("""
<style>
/* ชื่อ QUEST */
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2 {
    color: #eaf2ff;
    font-weight: 800;
    letter-spacing: 2px;
}

/* พื้นที่เมนูแต่ละรายการ */
section[data-testid="stSidebar"] div[role="radiogroup"] {
    gap: 10px;
}

/* เมนูปกติ */
section[data-testid="stSidebar"] div[role="radiogroup"] label {
    background-color: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(160, 190, 230, 0.18);
    border-radius: 14px;
    padding: 14px 16px;
    min-height: 54px;
    transition: background-color 0.2s ease,
                border-color 0.2s ease;
}

/* เมื่อนำเมาส์ไปชี้ */
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    background-color: rgba(75, 145, 230, 0.20);
    border-color: #75baff;
}


/* ซ่อนวงกลม Radio */
section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {
    display: none !important;
}

/* รูปแบบแถบเมนู */
section[data-testid="stSidebar"] div[role="radiogroup"] label {
    display: flex !important;
    align-items: center !important;
    background-color: rgba(255, 255, 255, 0.06) !important;
    border: 1px solid rgba(160, 190, 230, 0.18) !important;
    border-radius: 14px !important;
    padding: 14px 16px !important;
    min-height: 54px !important;
    gap: 0 !important;
    transition: background-color 0.2s ease, border-color 0.2s ease;
}

/* เมื่อนำเมาส์ไปชี้ */
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    background-color: rgba(75, 145, 230, 0.20) !important;
    border-color: #75baff !important;
}

/* ข้อความเมนู */
section[data-testid="stSidebar"] div[role="radiogroup"] label p {
    font-size: 16px !important;
    font-weight: 600 !important;
    margin: 0 !important;
}

/* ซ่อนวงกลมและสีของตัวเลือก Radio */
section[data-testid="stSidebar"] div[role="radiogroup"] input[type="radio"],
section[data-testid="stSidebar"] div[role="radiogroup"] label svg {
    display: none !important;
}

# ------------------------------------------
# MENU: หน้าแรก & สรุปผล
# ------------------------------------------
if menu == "🎯สรุปผล":
    st.subheader("🏆 สรุปเป้าหมาย")
    st.write("ยินดีต้อนรับ นี่คือภาพรวมในตอนนี้")
    
    # แสดงกล่องสถานะเงินออมปัจจุบัน
    st.metric(label="เงินเก็บปัจจุบันของคุณ", value=f"{st.session_state.balance:,.2f} บาท")
    st.text(f"🎯 Goal : {st.session_state.item_name} ราคา {st.session_state.goal:,.2f} บาท")
    
    # ตรรกะแจ้งเตือนเงินออมดั้งเดิมของคุณ
    
    far = st.session_state.goal - st.session_state.balance
    unfar = st.session_state.balance - st.session_state.goal

    if st.session_state.goal > 0:
        if far > 0:
            messages = [
                f"คุณยังขาดเงินอีก {far:,.2f} บาทนะ แล้ว **{st.session_state.item_name}** ที่คุณอยากได้ล่ะ?",
                f"ขาดอีกแค่ {far:,.2f} บาทเองงงง อีกนิดเดียวก็ได้แล้ว 🤏🤏",
                f"เอ้าท่องพร้อมกันนน เพื่อ **{st.session_state.item_name}** เพื่อ **{st.session_state.item_name}** เพื่อ **{st.session_state.item_name}** 😀",
                "อย่าเพิ่งยอมแพ้ ความสำเร็จมันต้องใช้เวลานะ! 👊",
                "วันนี้อาจยังไม่ถึง แต่คุณต้องทำได้แน่!",
                f"ลำบากตอนนี้ เดี๋ยวตอนได้ **{st.session_state.item_name}** ก็สบายแล้ววว 😣😣"
            ]
            message = random.choice(messages)
            st.info(message)

        elif far == 0:
            messages = [
                f"เย้!! คุณสามารถซื้อ **{st.session_state.item_name}** ได้แล้ว 🎉🎉",
                "ยินดีด้วยยยย คุณทำสำเร็จแล้ว!",
                "ได้แล้วววว นี่แหละชัยชนะ ฮ่าฮ่าฮ่า",
                f"เห็นมั้ยล่ะ **{st.session_state.item_name}** อยู่ใกล้แค่เอื้อมเท่านั้นแหละ",
                "สบายมาก 💪💪",
                "ได้เวลาสำหรับของชิ้นต่อไปแล้ว 🤩🤩"
            ]
            message = random.choice(messages)
            st.info(message)

        else:
            messages = [
                f"ตอนนี้คุณสามารถซื้อ **{st.session_state.item_name}** ได้เป็นร้อยอันแล้วม้าง",
                "คุณนี่อัจฉริยะด้านการเก็บเงินชัดๆ!!",
                f"ทำได้แล้วว และยังมีเงินเกินมาอีกตั้ง {unfar:,.2f} บาทแหละ",
                f"เห็นมั้ยล่ะ **{st.session_state.item_name}** อยู่ใกล้แค่เอื้อมเท่านั้นแหละ",
                "สบายมาก 💪💪",
                "คุณมีเงินเกินแล้ว ซื้อได้ทั้งบริษัทแล้วมั้งเนี่ย 💰",
                "อนาคตเศรษฐีพันล้านรึป่าวเนี่ยย 💸💸"
            ]
            message = random.choice(messages)
            st.info(message)


# ------------------------------------------
# MENU: Money Line
# ------------------------------------------
elif menu == "💰 Money Line":
    st.subheader("💰 Money Line: วางแผนการเงินเพื่อเป้าหมาย")

    # ช่องรับข้อมูลเป้าหมายเฉพาะเจาะจง
    item = st.text_input(
        "คุณกำลังเก็บเงินไปเพื่อซื้ออะไร? (เช่น หูฟัง, เกม):",
        value=st.session_state.item_name
    )
    target_goal = st.number_input(
        "ของชิ้นนั้นราคากี่บาท?:",
        min_value=0.0,
        value=st.session_state.goal,
        step=100.0
    )

    if st.button("บันทึกเป้าหมายการซื้อของ"):
        try:
            supabase.table("player_data").update({
                "item": item,
                "goal": str(target_goal)
            }).eq(
                "user_id", st.session_state["user_id"]
            ).execute()

            st.session_state.item_name = item
            st.session_state.goal = target_goal

            st.success("บันทึกข้อมูลเป้าหมายใหม่เรียบร้อยแล้ว!")

        except Exception as e:
            st.error(f"บันทึกเป้าหมายไม่สำเร็จ: {e}")
    
    st.write("---")
    st.write("### บันทึกรายรับ-รายจ่ายของวันนี้")
    income = st.number_input("วันนี้ได้เงินกี่บาท💰:", min_value=0.0, value=0.0)
    expense = st.number_input("วันนี้ใช้จ่ายกี่บาท💸:", min_value=0.0, value=0.0)
    
    
    if st.button("คำนวณและบันทึกยอดเงินวันนี้"):
        try:
            new_balance = (
                st.session_state.balance + income - expense
            )

            supabase.table("player_data").update({
                "balance": new_balance
            }).eq(
                "user_id", st.session_state["user_id"]
            ).execute()

            st.session_state.balance = new_balance

            st.success(
                "อัปเดตกระเป๋าเงินเรียบร้อยแล้ว! "
                "ลองกลับไปดูหน้าแรกเพื่อเช็กยอดเงิน"
            )

        except Exception as e:
            st.error(f"บันทึกยอดเงินไม่สำเร็จ: {e}")


    st.write("---")
    st.subheader("🧹 จัดการเงินเก็บ")

    if st.button("ล้างเงินเก็บ", key="reset_balance"):
        st.session_state["confirm_reset_balance"] = True

    if st.session_state.get("confirm_reset_balance", False):
        st.warning(
            "⚠️ คุณกำลังจะตั้งยอดเงินเก็บเป็น 0 บาท "
            "การดำเนินการนี้ไม่สามารถย้อนกลับได้ "
            "แต่ชื่อเป้าหมายและราคาเป้าหมายจะไม่ถูกลบ"
        )

        confirm_col, cancel_col = st.columns(2)


        with confirm_col:
            if st.button("ยืนยันล้างเงินเก็บ", key="btn_confirm_reset_balance"):
                try:
                    supabase.table("player_data").update({
                        "balance": 0
                    }).eq(
                        "user_id", st.session_state["user_id"]
                    ).execute()

                    st.session_state.balance = 0.0
                    st.session_state["show_reset_balance_confirm"] = False
                    st.success("ล้างเงินเก็บเรียบร้อยแล้ว!")
                    st.rerun()

                except Exception as e:
                    st.error(f"ล้างเงินเก็บไม่สำเร็จ: {e}")

        with cancel_col:
            if st.button("ยกเลิก", key="btn_cancel_reset_balance"):
                st.session_state["show_reset_balance_confirm"] = False
                st.rerun()

    st.caption(
        "หมายเหตุ: ปุ่มนี้จะล้างเฉพาะยอดเงินเก็บของบัญชีที่เข้าสู่ระบบ "
        "ไม่ลบชื่อสิ่งของหรือราคาเป้าหมาย"
    )


    
# ------------------------------------------
# MENU: Health Line
# ------------------------------------------
elif menu == "💪 Health Line":
    st.subheader("เช็คลิสต์ร่างกายประจำวัน")
    st.write("🌱 สุขภาพที่ดีเริ่มจากสิ่งเล็ก ๆ ที่คุณทำในทุกวัน มาเช็คไปพร้อมกันเลย !😁")
    
        # ฟังก์ชันสุ่มข้อความและแสดงสถานะภารกิจ
    def show_health_status(key, done, total, messages, success):
        if done == total:
            st.success(success)
        else:
            if key not in st.session_state:
                st.session_state[key] = random.choice(messages)

            st.markdown(
                f"<p style='color:#e05252; font-size:12px;'>"
                f"💬 {st.session_state[key]}</p>",
                unsafe_allow_html=True
            )

        st.caption(f"ความคืบหน้า: {done}/{total}")
        st.progress(done / total)


    # 1. ภารกิจดื่มน้ำ
    with st.expander("💧 ภารกิจที่ 1: วันนี้ดื่มน้ำครบ 8 แก้วหรือยัง?"):
        st.write("เติมพลังให้ร่างกาย จิบน้ำให้เหมาะกับความต้องการของตัวเอง!")

        water_cols = st.columns(4)
        water_done = []

        for i in range(8):
            with water_cols[i % 4]:
                checked = st.checkbox(
                    f"แก้วที่ {i + 1}",
                    key=f"water_{i + 1}"
                )
                water_done.append(checked)

        water_count = sum(water_done)

        # เลือกข้อความตามจำนวนแก้ว
        if water_count == 0:
            water_message = "วันนี้คุณยังไม่ได้เช็กการดื่มน้ำเลยนะ 💧"

        elif water_count <= 3:
            water_message = "ปากแห้งเป็นทะเลทรายแล้วมั้งเนี่ย 🏜️"

        elif water_count < 8:
            # สุ่มใหม่เมื่อจำนวนแก้วเปลี่ยน
            previous_count = st.session_state.get(
                "previous_water_count", -1
            )

            if water_count != previous_count:
                st.session_state["water_tip"] = random.choice([
                    "พักแล้วจิบน้ำสักหน่อยมั้ยย 💧",
                    "น้ำช่วยให้ร่างกายทำงานได้ดีตามปกตินะ อย่าลืมล่ะ!",
                    "ไม่ต้องรีบดื่มรวดเดียว ค่อย ๆ จิบระหว่างวันเอานะ 😉😉"
                ])

            water_message = st.session_state.get(
                "water_tip",
                "พักแล้วจิบน้ำสักหน่อยมั้ยย 💧"
            )

        else:
            water_message = None

        
        # แสดงข้อความตามจำนวนแก้วและเปลี่ยนสี
        if water_count == 8:
            st.success("ภารกิจเช็กการดื่มน้ำครบแล้ว! เยี่ยมเลย 💧")

        elif water_count == 0:
            st.markdown(
                "<p style='color:#E53935; font-size:12px;'>"
                "💬 วันนี้คุณยังไม่ได้เช็กการดื่มน้ำเลยนะ 💧</p>",
                unsafe_allow_html=True
            )

        elif water_count <= 3:
            st.markdown(
                f"<p style='color:#F39C12; font-size:12px;'>"
                f"💬 {water_message}</p>",
                unsafe_allow_html=True
            )


        else:
            st.markdown(
                f"<p style='color:#3498DB; font-size:12px;'>"
                f"💬 {water_message}</p>",
                unsafe_allow_html=True
            )


        st.session_state["previous_water_count"] = water_count

        st.caption(f"ความคืบหน้า: {water_count}/8")
        st.progress(water_count / 8)



    # 2. ภารกิจรับประทานอาหาร
    with st.expander("🍚 ภารกิจที่ 2: วันนี้กินอาหารครบ 3 มื้อหรือยัง?"):
        st.write("เติมพลังงานให้ร่างกายด้วยมื้ออาหารที่หลากหลาย")

        breakfast = st.checkbox("🌅 มื้อเช้า", key="meal_breakfast")
        lunch = st.checkbox("🌄 มื้อกลางวัน", key="meal_lunch")
        dinner = st.checkbox("🌆 มื้อเย็น", key="meal_dinner")

        meal_done = [breakfast, lunch, dinner]
        meal_count = sum(meal_done)
             
        # เลือกข้อความตามจำนวนมื้อ
        if meal_count == 0:
            meal_message = "วันนี้คุณยังไม่ได้กินอะไรเลยนะ 🫩"

        elif meal_count == 1:
            meal_message = "อาหารที่หลากหลายช่วยให้ร่างกายได้รับสารอาหารที่จำเป็นนะ! 💪"

        elif meal_count == 2:
            # สุ่มใหม่เมื่อจำนวนมื้อเปลี่ยน
            previous_count = st.session_state.get(
                "previous_meal_count", -1
            )

            if meal_count != previous_count:
                st.session_state["meal_tip"] = random.choice([
                    "อีกมื้อเดียวก็ครบแล้วนะ",
                    "อย่าลืมกินอาหารให้ครบ 5 หมู่ด้วยหล่ะ 😌",
                    "อย่าลืมหาเวลากินมื้อที่เหลือนะ 😉😉"
                ])

            meal_message = st.session_state.get(
                "meal_tip",
                "อย่าลืมกินอาหารให้ครบ 5 หมู่ด้วยหล่ะ 😌"
            )

        else:
            meal_message = None


                 # แสดงข้อความตามจำนวนมื้อท่ีกินและเปลี่ยนสี
        if meal_count == 3:
            st.success("บันทึกมื้ออาหารครบทั้ง 3 มื้อแล้ว! เก่งมาก 🍚")


        elif meal_count == 0:
            st.markdown(
                "<p style='color:#E53935; font-size:12px;'>"
                "💬 วันนี้คุณยังไม่ได้กินอะไรเลยนะ 🍚</p>",
                unsafe_allow_html=True
            )

        elif meal_count == 1:
            st.markdown(
                f"<p style='color:#F39C12; font-size:12px;'>"
                f"💬 {meal_message}</p>",
                unsafe_allow_html=True
            )


        else:
            st.markdown(
                f"<p style='color:#3498DB; font-size:12px;'>"
                f"💬 {meal_message}</p>",
                unsafe_allow_html=True
            )


        st.session_state["previous_meal_count"] = meal_count

        st.caption(f"ความคืบหน้า: {meal_count}/3 มื้อ")
        st.progress(meal_count / 3)



    # 3. ภารกิจกินอาหารให้สม่ำเสมอ
    with st.expander("⏰ ภารกิจที่ 3: วันนี้ได้พักกินข้าวเป็นเวลาหรือยัง?"):
        st.write("หาเวลาพักกินอาหาร ไม่ปล่อยให้กิจกรรมต่าง ๆ เบียดเวลามื้ออาหาร")

        breakfast_time = st.checkbox(
            "จัดเวลามื้อเช้าได้เหมาะสม",
            key="time_breakfast"
        )
        lunch_time = st.checkbox(
            "มีเวลาพักกินมื้อกลางวัน",
            key="time_lunch"
        )
        dinner_time = st.checkbox(
            "จัดเวลามื้อเย็นได้เหมาะสม",
            key="time_dinner"
        )

        time_count = sum([
            breakfast_time,
            lunch_time,
            dinner_time
        ])

        show_health_status(
            "time_tip",
            time_count,
            3,
            [
                "ภารกิจในเกมรอได้ แต่ท้องร้องนี่สิไม่ยอมรอ 😂",
                "อย่าลืมพักจากการเรียนหรือเล่นเกมมากินข้าวนะ!",
                "การกินอาหารสม่ำเสมอช่วยให้จัดกิจวัตรได้ดีขึ้น 🍱"
            ],
            "วันนี้จัดเวลามื้ออาหารได้ครบแล้ว! ⏰"
        )

    # 4. ภารกิจการนอน
    with st.expander("🛌 ภารกิจที่ 4: วันนี้พักผ่อนเพียงพอหรือยัง?"):
        st.write("การนอนช่วยให้ร่างกายและสมองได้พักฟื้น")

        sleep_enough = st.checkbox(
            "เมื่อคืนได้นอนเพียงพอสำหรับตัวเอง",
            key="sleep_enough"
        )
        sleep_schedule = st.checkbox(
            "พยายามเข้านอนและตื่นให้เป็นเวลา",
            key="sleep_schedule"
        )
        screen_break = st.checkbox(
            "เตรียมตัวพักจากหน้าจอก่อนนอน",
            key="sleep_screen"
        )

        sleep_count = sum([
            sleep_enough,
            sleep_schedule,
            screen_break
        ])

        show_health_status(
            "sleep_tip",
            sleep_count,
            3,
            [
                "ตัวละครยังต้องพักฟื้น แล้วคุณล่ะ? 😂",
                "นอนดึกทุกคืน เดี๋ยวพรุ่งนี้สมองขอโหลดช้านะ 💤",
                "วัยรุ่นส่วนใหญ่มักต้องการนอนประมาณ 8–10 ชั่วโมงต่อคืน",
                "ลองวางมือถือก่อนนอน แล้วให้สมองได้พักบ้างนะ 📱"
            ],
            "ภารกิจดูแลการนอนครบแล้ว ขอให้พักผ่อนเต็มที่! 💤"
        )

    # 5. ภารกิจเคลื่อนไหวร่างกาย
    with st.expander("🚶 ภารกิจที่ 5: วันนี้ได้ขยับร่างกายหรือยัง?"):
        st.write("ไม่จำเป็นต้องออกกำลังหนัก เริ่มจากการเคลื่อนไหวที่เหมาะกับตัวเองได้")

        walk = st.checkbox(
            "🚶 เดินหรือขยับร่างกายระหว่างวัน",
            key="move_walk"
        )
        stretch = st.checkbox(
            "🙆 ยืดเหยียดร่างกาย",
            key="move_stretch"
        )
        activity = st.checkbox(
            "⚽ ทำกิจกรรมที่ชอบ เช่น เล่นกีฬา",
            key="move_activity"
        )

        move_count = sum([walk, stretch, activity])

        show_health_status(
            "move_tip",
            move_count,
            3,
            [
                "อย่านั่งนิ่งจนรากงอกเหมือนต้นไม้สิ 😂",
                "ลุกมายืดเส้นสักนิด ร่างกายจะได้เปลี่ยนอิริยาบถ!",
                "การเคลื่อนไหวสม่ำเสมอดีต่อสุขภาพนะ ไม่จำเป็นต้องหักโหม 💪"
            ],
            "ภารกิจขยับร่างกายครบแล้ว เยี่ยมมาก! 🚶"
        )

    # 6. ภารกิจพักใจ
    with st.expander("💚 ภารกิจที่ 6: วันนี้ได้ดูแลความรู้สึกตัวเองหรือยัง?"):
        st.write("การพักใจเป็นส่วนหนึ่งของการดูแลตัวเองเหมือนกันนะ")

        relax = st.checkbox(
            "หาเวลาพักจากสิ่งที่ทำอยู่",
            key="mind_relax"
        )
        enjoy = st.checkbox(
            "ทำกิจกรรมที่ทำให้ตัวเองมีความสุข",
            key="mind_enjoy"
        )
        connect = st.checkbox(
            "พูดคุยกับคนที่ไว้ใจเมื่ออยากระบาย",
            key="mind_connect"
        )

        mind_count = sum([relax, enjoy, connect])

        show_health_status(
            "mind_tip",
            mind_count,
            3,
            [
                "คุณไม่ใช่หุ่นยนต์นะ พักบ้างก็ได้ 🤖",
                "ไม่จำเป็นต้องเก่งทุกนาที แค่วันนี้ดูแลตัวเองได้ก็ดีแล้ว 💚",
                "พักใจสักนิด ไม่ใช่การแพ้ แต่เป็นการให้เวลากับตัวเอง"
            ],
            "ภารกิจดูแลใจสำเร็จแล้ว อย่าลืมใจดีกับตัวเองนะ 💚"
        )

    st.write("---")
    st.caption("💚 เช็กลิสต์นี้มีไว้ช่วยติดตามการดูแลตัวเอง การทำได้ครบทุกข้อเป็นเรื่องดี แต่สิ่งสำคัญคือการดูแลตัวเองอย่างเหมาะสมและสม่ำเสมอในทุก ๆ วันนะ!")
    
    
    if st.button("บันทึกคะแนนสุขภาพประจำวัน"):
        st.success("บันทึกพฤติกรรมเรียบร้อย! รักษาวินัยแบบนี้ในทุกๆ วันนะครับ")

# ------------------------------------------
# 🧹 ปุ่มล้างข้อมูลทั้งหมด (เมนูด้านซ้ายล่าง)
# ------------------------------------------ผท
st.sidebar.write("---")
if st.sidebar.button("🧹 รีเซ็ตข้อมูลทั้งหมด"):
    for f in ["money.txt", "goal.txt", "item.txt"]:
        if os.path.exists(f):
            os.remove(f)
    st.session_state.balance = 0.0
    st.session_state.goal = 0.0
    st.session_state.item_name = "สิ่งที่อยากได้"
    st.sidebar.warning("ล้างข้อมูลเรียบร้อยแล้ว!")
    st.rerun()