"""
Supabase Auth — email/password + Google OAuth.
Manages session state in Streamlit.
"""
import os
import streamlit as st
from supabase import create_client, Client


def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_ANON_KEY"]
    return create_client(url, key)


def sign_up(email: str, password: str, full_name: str = ""):
    client = get_client()
    return client.auth.sign_up({
        "email": email,
        "password": password,
        "options": {"data": {"full_name": full_name}},
    })


def sign_in(email: str, password: str):
    client = get_client()
    return client.auth.sign_in_with_password({"email": email, "password": password})


def sign_out():
    try:
        get_client().auth.sign_out()
    except Exception:
        pass
    for key in ["session", "user", "db", "agent", "chat_messages"]:
        st.session_state.pop(key, None)


def get_google_oauth_url() -> str:
    client = get_client()
    redirect = os.environ.get(
        "OAUTH_REDIRECT_URL",
        "https://ai-bookkeeping-agent.streamlit.app/"
    )
    res = client.auth.sign_in_with_oauth({
        "provider": "google",
        "options": {
            "redirect_to": redirect,
            "scopes": "email profile",
        }
    })
    return res.url


def handle_oauth_callback() -> bool:
    """Catch access_token from URL after Supabase OAuth redirect."""
    try:
        params = st.query_params
        access_token = params.get("access_token", "")
        refresh_token = params.get("refresh_token", "") or access_token
        if access_token:
            client = get_client()
            res = client.auth.set_session(access_token, refresh_token)
            if res and res.session:
                st.session_state.session = res.session
                st.session_state.user = res.user
                st.query_params.clear()
                return True
    except Exception:
        pass
    return False


def is_authenticated() -> bool:
    return bool(st.session_state.get("session"))


def get_access_token() -> str:
    session = st.session_state.get("session")
    return session.access_token if session else ""


def get_user():
    return st.session_state.get("user")


def render_auth_page():
    """Full-screen login / signup UI."""
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&display=swap');
html,body,[class*="css"]{font-family:'Source Sans 3','Segoe UI',sans-serif!important}
#MainMenu,footer,header,[data-testid="manage-app-button"],[data-testid="stToolbarActions"]{display:none!important}
.stApp{background:#f4f5f7!important}
.stTabs [data-baseweb="tab-list"]{gap:8px}
.stTabs [data-baseweb="tab"]{border-radius:8px 8px 0 0;font-weight:600}
.google-btn{display:flex;align-items:center;justify-content:center;gap:10px;background:white;border:1.5px solid #dfe6e9;border-radius:8px;padding:10px 16px;font-size:14px;font-weight:600;color:#2c3e50;text-decoration:none;cursor:pointer;width:100%;margin-bottom:16px}
.google-btn:hover{background:#f8f9fa}
.divider-line{text-align:center;color:#b2bec3;font-size:13px;margin:12px 0;border-bottom:1px solid #dfe6e9;line-height:0}
.divider-line span{background:#fff;padding:0 10px}
</style>
""", unsafe_allow_html=True)

    col = st.columns([1, 2, 1])[1]
    with col:
        st.markdown("""
<div style="text-align:center;padding:32px 0 24px">
    <div style="font-size:48px">📗</div>
    <div style="font-size:26px;font-weight:800;color:#1a1a2e;margin:8px 0 4px">AI Books</div>
    <div style="font-size:14px;color:#7f8c8d">Smart bookkeeping powered by Claude AI</div>
</div>
""", unsafe_allow_html=True)

        tab_login, tab_signup = st.tabs(["Sign In", "Create Account"])

        with tab_login:
            # Google OAuth button
            try:
                google_url = get_google_oauth_url()
                st.markdown(
                    f'<a href="{google_url}" target="_self" class="google-btn">'
                    f'<img src="https://www.google.com/favicon.ico" width="18"> '
                    f'Continue with Google</a>',
                    unsafe_allow_html=True,
                )
            except Exception:
                st.markdown('<div style="text-align:center;color:#b2bec3;font-size:12px;padding:8px">Google OAuth not configured</div>', unsafe_allow_html=True)

            st.markdown('<div class="divider-line"><span>or sign in with email</span></div>', unsafe_allow_html=True)

            email_in = st.text_input("Email", key="login_email", placeholder="you@example.com")
            pass_in  = st.text_input("Password", key="login_pass", type="password", placeholder="••••••••")

            if st.button("Sign In →", type="primary", use_container_width=True, key="login_btn"):
                if not email_in or not pass_in:
                    st.error("Please enter email and password.")
                else:
                    with st.spinner("Signing in..."):
                        try:
                            res = sign_in(email_in, pass_in)
                            if res.session:
                                st.session_state.session = res.session
                                st.session_state.user = res.user
                                st.rerun()
                            else:
                                st.error("Invalid credentials.")
                        except Exception as e:
                            st.error(f"Sign in failed: {str(e)[:120]}")

        with tab_signup:
            name_up  = st.text_input("Full Name", key="su_name", placeholder="Juan dela Cruz")
            email_up = st.text_input("Email", key="su_email", placeholder="you@example.com")
            pass_up  = st.text_input("Password (min 8 chars)", key="su_pass",
                                     type="password", placeholder="••••••••")

            if st.button("Create Account →", type="primary", use_container_width=True, key="signup_btn"):
                if not email_up or not pass_up or not name_up:
                    st.error("Name, email and password are required.")
                elif len(pass_up) < 8:
                    st.error("Password must be at least 8 characters.")
                else:
                    with st.spinner("Creating account..."):
                        try:
                            res = sign_up(email_up, pass_up, name_up)
                            if res.user:
                                st.success("✅ Account created! Check your email to confirm, then sign in.")
                            else:
                                st.error("Signup failed. Try again.")
                        except Exception as e:
                            st.error(f"Signup error: {str(e)[:120]}")

        st.markdown('<div style="text-align:center;margin-top:20px;font-size:11px;color:#b2bec3">Secure · RLS-protected · Philippine tax-aware</div>', unsafe_allow_html=True)
