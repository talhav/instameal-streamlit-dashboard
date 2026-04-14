import streamlit as st

st.set_page_config(page_title="Instameals RecSys UI", layout="wide")

pages = [
    st.Page("pages/first_recommendation.py", title="First Recommendation", default=True),
    st.Page("pages/nth_recommendation.py", title="Nth Recommendation"),
]

pg = st.navigation(pages)

pg.run()
