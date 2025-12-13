import os
import streamlit as st

st.set_page_config(page_title="Collective Garden — Safe Mode", page_icon="🌱")

st.title("🌱 Collective Garden — Safe Mode")
st.write("If you can see this, Streamlit Cloud is running your code ✅")

st.subheader("Repo files")
st.write(os.listdir("."))

st.subheader("Assets folder")
if os.path.isdir("assets"):
    st.write(os.listdir("assets"))
else:
    st.error("No assets/ folder found in the deployed repo.")



