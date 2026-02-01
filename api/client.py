import streamlit as st
import requests

class ApiClient:
    def __init__(self):
        self._token = self._get_token()

    def _get_token(self):
        if "api" in st.secrets and "jwt_token" in st.secrets["api"]:
            return st.secrets["api"]["jwt_token"]
        st.warning("API Token not found in secrets. Please configure [api] jwt_token in secrets.toml")
        return None

    def _get_headers(self):
        headers = {
            "Content-Type": "application/json"
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def get(self, url, params=None):
        return requests.get(url, headers=self._get_headers(), params=params)

    def post(self, url, json_data=None):
        return requests.post(url, headers=self._get_headers(), json=json_data)
