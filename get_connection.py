import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st

@st.cache_resource
def get_connection():
    return psycopg2.connect(
        dbname=st.secrets["dbname"],
        user=st.secrets["user"],
        password=st.secrets["password"],
        host=st.secrets["host"],
        port=st.secrets["port"],
        cursor_factory=RealDictCursor
    )