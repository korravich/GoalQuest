import streamlit as st
import os
import random

# ตั้งค่าหน้าตาของเว็บไซต์ให้น่ารักและจัดกึ่งกลาง
st.set_page_config(page_title="Goal Quest", page_icon="⚔️", layout="centered")
st.title("⚔️ Goal Quest ⚔️")
st.caption("Your Future Depends on What You Do Today (beta)")
st.write("---")

# ==========================================
# 💾 ระบบหลังบ้าน: โหลดข้อมูลจากไฟล์ .txt
# ==========================================
if "balance" not in st.session_state:
    try:
        with open("money.txt", "r", encoding="utf-8") as file:
            st.session_state.balance = float(file.read())
    except FileNotFoundError:
        st.session_state.balance = 0.0

if "goal" not in st.session_state:
    try:
        with open("goal.txt", "r", encoding="utf-8") as file:
            st.session_state.goal = float(file.read())
    except FileNotFoundError:
        st.session_state.goal = 0.0

if "item_name" not in st.session_state:
    try:
        with open("item.txt", "r", encoding="utf-8") as file:
            st.session_state.item_name = file.read()
    except FileNotFoundError:
        st.session_state.item_name = "สิ่งที่อยากได้"

# ==========================================
# 🧭 ระบบเมนูหลัก (Sidebar ด้านข้าง)
# ==========================================
menu = st.sidebar.radio("เลือกภารกิจของคุณ:", ["📊 หน้าแรก & สรุปผลรวม", "💰 Money Line", "🧘‍♂️ Health Line"])

# ------------------------------------------
# MENU: หน้าแรก & สรุปผลรวม
# ------------------------------------------
if menu == "📊 หน้าแรก & สรุปผลรวม":
    st.subheader("🏆 สรุปเป้าหมาย")
    st.write("ยินดีต้อนรับ นี่คือภาพรวมในตอนนี้")
    
    # แสดงกล่องสถานะเงินออมปัจจุบัน
    st.metric(label="เงินเก็บปัจจุบันของคุณ", value=f"{st.session_state.balance:,.2f} บาท")
    st.text(f"🎯 Goal: {st.session_state.item_name} (ราคา {st.session_state.goal:,.2f} บาท)")
    
    # ตรรกะแจ้งเตือนเงินออมดั้งเดิมของคุณ
    
    far = st.session_state.goal - st.session_state.balance
    unfar = st.session_state.balance - st.session_state.goal

    if st.session_state.goal > 0:
        if far > 0:
            messages = [
                f"คุณยังขาดเงินอีก {far:,.2f} บาทนะ แล้ว **{st.session_state.item_name}** ที่คุณอยากได้ล่ะ?",
                f"ขาดอีกแค่ {far:,.2f} บาทเองงงง อีกนิดเดียวก็ได้แล้ว 🤏🤏",
                f"เอ้าท่องพร้อมกันนน เพื่อ **{st.session_state.item_name}** เพื่อ **{st.session_state.item_name}** 😀",
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
    item = st.text_input("คุณกำลังเก็บเงินไปเพื่อซื้ออะไร? (เช่น หูฟัง, เกม):", value=st.session_state.item_name)
    target_goal = st.number_input("ของชิ้นนั้นราคากี่บาท?:", min_value=0.0, value=st.session_state.goal, step=100.0)
    
    if st.button("บันทึกเป้าหมายการซื้อของ"):
        st.session_state.item_name = item
        st.session_state.goal = target_goal
        with open("item.txt", "w", encoding="utf-8") as file:
            file.write(item)
        with open("goal.txt", "w", encoding="utf-8") as file:
            file.write(str(target_goal))
        st.success("บันทึกข้อมูลเป้าหมายใหม่เรียบร้อยแล้ว!")
    
    st.write("---")
    st.write("### บันทึกรายรับ-รายจ่ายของวันนี้")
    income = st.number_input("วันนี้ได้เงินกี่บาท💰:", min_value=0.0, value=0.0)
    expense = st.number_input("วันนี้ใช้จ่ายกี่บาท💸:", min_value=0.0, value=0.0)
    
    if st.button("คำนวณและบันทึกยอดเงินวันนี้"):
        # ตรรกะบวกสมุดบัญชีเดิมของคุณ
        st.session_state.balance = st.session_state.balance + income - expense
        with open("money.txt", "w", encoding="utf-8") as file:
            file.write(str(st.session_state.balance))
            
        st.success("อัปเดตกระเป๋าเงินออนไลน์เรียบร้อยแล้ว! ลองกลับไปดูหน้าแรกเพื่อเช็คสถานะเป้าหมาย")

# ------------------------------------------
# MENU: Health Line
# ------------------------------------------
elif menu == "🧘‍♂️ Health Line":
    st.subheader("🧘‍♂️ Health Line: เช็คลิสต์ความสมดุลของร่างกายประจำวัน")
    st.write("วันนี้คุณรักษาสุขภาพพื้นฐานครบถ้วนแล้วหรือยัง? ติ๊กถูกเพื่อบันทึกสถิติ:")
    
    # ระบบเช็คลิสต์พฤติกรรมพื้นฐานเข้าถึงง่ายสำหรับทุกคน
    water = st.checkbox("💧 วันนี้ดื่มน้ำครบ 8 แก้ว (ประมาณ 2 ลิตร)")
    meals = st.checkbox("🍚 วันนี้กินข้าวครบทั้ง 3 มื้อ")
    on_time = st.checkbox("⏰ วันนี้กินข้าวตรงเวลา ไม่ปล่อยให้ท้องว่าง")
    sleep = st.checkbox("🛌 นอนหลับพักผ่อนเต็มอิ่ม (7-8 ชั่วโมง)")
    move = st.checkbox("🚶 ได้ขยับร่างกายเบาๆ ยืดเส้นยืดสาย หรือเดินสลับระหว่างวัน")
    
    if st.button("บันทึกคะแนนสุขภาพประจำวัน"):
        st.success("บันทึกพฤติกรรมเรียบร้อย! รักษาวินัยแบบนี้ในทุกๆ วันนะครับ")

# ------------------------------------------
# 🧹 ปุ่มล้างข้อมูลทั้งหมด (เมนูด้านซ้ายล่าง)
# ------------------------------------------
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