import streamlit as st
import pandas as pd

def gsheets_doctor(conn, worksheet="Scores"):
    st.subheader("GSHEETS CONNECTION DOCTOR 🚑")
    # 1. Connection test
    if conn is None:
        st.error("❌ Google Sheets connection not initialized. Check credentials and config.")
        return False

    # 2. Read test
    try:
        df = conn.read(worksheet=worksheet)
        st.success("✅ Connection established.")
    except Exception as e:
        st.error(f"❌ Failed to read '{worksheet}'. Error: {e}")
        return False

    # 3. Columns diagnostic
    expected_cols = ['Tag', 'Name', 'USN', 'Time']
    missing = [c for c in expected_cols if c not in df.columns]
    st.write("Sheet columns found:", list(df.columns))
    if missing:
        st.error(f"❌ Columns missing: {missing}. Must match: {expected_cols}")
        return False
    else:
        st.success(f"✅ All required columns present.")

    # 4. Write test
    test_row = {"Tag": "DOC", "Name": "Test Name", "USN": "1MS22AIDOC", "Time": 0.0}
    try:
        conn.write(worksheet=worksheet, data=pd.DataFrame([test_row]), append=True)
        st.success("✅ Write test passed: Able to append a row.")
    except Exception as e:
        st.error(f"❌ Failed to write to sheet. Error: {e}")
        return False

    st.info("GSHEETS DOCTOR PASSED. Sheet is ready for read/write!")
    return True

# Usage in your app:
if st.button("Run Connection Doctor"):
    gsheets_doctor(conn, worksheet="Scores")
