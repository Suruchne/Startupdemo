import streamlit as st


def apply_brand():
    st.markdown("""
    <style>
    html, body, [class*="css"] {font-family:"Trebuchet MS","Arial Rounded MT Bold",Arial,sans-serif; color:#123B3A;}
    .block-container {max-width:1450px; padding-top:1.5rem;}
    h1,h2,h3 {color:#087F7A; letter-spacing:-.025em;}
    .resmap-hero {background:linear-gradient(120deg,#087F7A,#20A39E); color:white; padding:2rem 2.2rem; border-radius:26px; border-bottom:9px solid #E6AD27; margin-bottom:1.2rem;}
    .resmap-hero h1 {color:white; margin:0; font-size:3rem;}
    .resmap-hero p {color:#FFF0B8; font-size:1.15rem; margin:.55rem 0 0;}
    .resmap-card {background:#F5FBFA; border:2px solid #B7DEDA; border-radius:22px; padding:1.25rem; min-height:165px;}
    .resmap-card b {color:#087F7A; font-size:1.08rem;}
    .resmap-step {background:#FFFFFF; border:2px solid #D8E9E7; border-top:8px solid #F28C28; border-radius:20px; padding:1.1rem; min-height:145px;}
    .resmap-note {background:#FFF5D8; border-left:7px solid #E6AD27; border-radius:14px; padding:1rem 1.2rem;}
    div[data-testid="stMetric"] {background:#F5FBFA; border:2px solid #B7DEDA; border-radius:18px; padding:1rem;}
    div[data-testid="stButton"] button, div[data-testid="stDownloadButton"] button {border-radius:18px; font-weight:700;}
    </style>
    """, unsafe_allow_html=True)


def hero(title, subtitle):
    st.markdown(f'<div class="resmap-hero"><h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)

