"""
Supabase Auth — email/password + Google OAuth.
Manages session state in Streamlit.
"""
import os
import streamlit as st
from supabase import create_client, Client


def get_client() -> Client:
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_ANON_KEY"],
    )


def sign_up(email: str, password: str, full_name: str = "") -> dict:
    client = get_client()
    res = client.auth.sign_up({
        "email": email,
        "password": password,
        "options": {"data": {"full_name": full_name}},
    })
    return res


def sign_in(email: str, password: str) -> dict:
    client = get_client()
    res = client.auth.sign_in_with_password({"email": email, "password": password})
    return res


def sign_out():
    try:
        client = get_client()
        client.auth.sign_out()
    except Exception:
        pass
    for key in ["session", "user", "db", "agent", "chat_messages"]:
        st.session_state.pop(key, None)


def get_google_oauth_url() -> str:
    client = get_client()
    res = client.auth.sign_in_with_oauth({
        "provider": "google",
        "options": {
            "redirect_to": os.environ.get(
                "OAUTH_REDIRECT_URL",
                "https://ai-bookkeeping-agent.streamlit.app/"
            ),
            "scopes": "email profile",
        }
    })
    return res.url


def is_authenticated() -> bool:
    if st.session_state.get("session"):
        return True
    # Check for OAuth callback tokens in URL
    try:
        params = st.query_params
        if params.get("access_token"):
            return False  # Let handle_oauth_callback() process it
    except Exception:
        pass
    return False


def get_access_token() -> str:
    session = st.session_state.get("session")
    if session:
        return session.access_token
    return ""


def get_user():
    return st.session_state.get("user")


def handle_oauth_callback():
    """Handle Supabase OAuth redirect — exchange URL token for session."""
    import urllib.parse
    try:
        # Streamlit puts query params in st.query_params
        params = st.query_params
        access_token = params.get("access_token", "")
        refresh_token = params.get("refresh_token", "")
        if access_token:
            client = get_client()
            session = client.auth.set_session(access_token, refresh_token)
            if session and session.session:
                st.session_state.session = session.session
                st.session_state.user = session.user
                st.query_params.clear()
                return True
    except Exception as e:
        pass
    return False


def render_auth_page():
    """Full-screen login/signup UI. Returns True when authenticated."""
    # Handle OAuth redirect callback first
    if handle_oauth_callback():
        st.rerun()
        return

    # Centered container
    st.markdown("""
    <style>
    .auth-wrap {
        max-width: 420px;
        margin: 60px auto 0 auto;
        background: white;
        border-radius: 12px;
        padding: 40px 36px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.10);
    }
    .auth-logo {
        font-size: 42px;
        text-align: center;
        margin-bottom: 4px;
    }
    .auth-title {
        font-size: 24px;
        font-weight: 800;
        text-align: center;
        color: #1a1a2e;
        margin-bottom: 4px;
    }
    .auth-sub {
        font-size: 14px;
        color: #7f8c8d;
        text-align: center;
        margin-bottom: 24px;
    }
    .google-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        background: white;
        border: 1.5px solid #dfe6e9;
        border-radius: 8px;
        padding: 10px;
        font-size: 14px;
        font-weight: 600;
        color: #2c3e50;
        text-decoration: none;
        margin-bottom: 16px;
        cursor: pointer;
        width: 100%;
    }
    .google-btn:hover { background: #f8f9fa; }
    .divider-text {
        text-align: center;
        color: #b2bec3;
        font-size: 13px;
        margin: 12px 0;
        position: relative;
    }
    .divider-text::before, .divider-text::after {
        content: '';
        position: absolute;
        top: 50%;
        width: 42%;
        height: 1px;
        background: #dfe6e9;
    }
    .divider-text::before { left: 0; }
    .divider-text::after  { right: 0; }
    </style>
    """, unsafe_allow_html=True)

    col = st.columns([1, 2, 1])[1]

    with col:
        st.markdown('<div class="auth-logo">📗</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-title">AI Books</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-sub">Smart bookkeeping powered by Claude AI</div>', unsafe_allow_html=True)

        tab_login, tab_signup = st.tabs(["Sign In", "Create Account"])

        with tab_login:
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
                            st.error(f"Sign in failed: {e}")

            st.markdown('<div class="divider-text">or</div>', unsafe_allow_html=True)

            try:
                google_url = get_google_oauth_url()
                st.markdown(
                    f'<a href="{google_url}" target="_self" class="google-btn">'
                    f'<img src="https://www.google.com/favicon.ico" width="18"> Continue with Google</a>',
                    unsafe_allow_html=True,
                )
            except Exception as e:
                st.caption(f"Google OAuth error: {e}")

        with tab_signup:
            name_up  = st.text_input("Full Name", key="su_name", placeholder="Juan dela Cruz")
            email_up = st.text_input("Email", key="su_email", placeholder="you@example.com")
            pass_up  = st.text_input("Password (min 8 chars)", key="su_pass",
                                     type="password", placeholder="••••••••")
            comp_up  = st.text_input("Business Name", key="su_company", placeholder="My Business")

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
                                st.success("✅ Account created! Please check your email to confirm, then sign in.")
                            else:
                                st.error("Signup failed. Try again.")
                        except Exception as e:
                            st.error(f"Signup error: {e}")

        st.markdown('<div style="text-align:center;margin-top:20px;font-size:11px;color:#b2bec3">Secure · GDPR-ready · Philippine tax-aware</div>', unsafe_allow_html=True)
