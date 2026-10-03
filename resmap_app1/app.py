import streamlit as st

st.set_page_config(page_title="ResMap", page_icon="🧬", layout="wide")

navigation = st.navigation(
    [
        st.Page("pages/0_Overview.py", title="Overview", icon="🏠", default=True),
        st.Page("pages/1_Genome_Evidence.py", title="Genome evidence", icon="🧬"),
        st.Page("pages/2_Experimental_Design.py", title="Experimental design", icon="🧪"),
    ]
)
navigation.run()
