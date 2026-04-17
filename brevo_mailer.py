"""
brevo_mailer.py
----------------
Handles all email notifications for SpeakAgain via the Brevo REST API.

Samuel uses Brevo with the custom domain bloomgatelaw.com (Samuel@bloomgatelaw.com).
This file uses the raw REST API (no SDK) — more reliable, fewer dependencies,
and works on Streamlit Community Cloud out of the box.

Brevo docs: https://developers.brevo.com/reference/send-transac-email
Free tier: 300 emails/day — plenty for a health app in testing phase.
"""

import os
import requests
import streamlit as st
from datetime import datetime
from typing import Optional


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

# Sender details — the Samuel@bloomgatelaw.com address must be verified
# in the Brevo dashboard under Settings > Senders & IPs before sending.
DEFAULT_SENDER_NAME = "SpeakAgain — Samuel Oluwakoya"
DEFAULT_SENDER_EMAIL = "Samuel@bloomgatelaw.com"


def _get_api_key() -> Optional[str]:
    """
    Read the Brevo API key from Streamlit secrets first, then environment.
    On Streamlit Cloud: add it to .streamlit/secrets.toml as BREVO_API_KEY.
    Locally: export BREVO_API_KEY="xkeysib-..." or put it in a .env file.
    """
    try:
        if "BREVO_API_KEY" in st.secrets:
            return st.secrets["BREVO_API_KEY"]
    except Exception:
        # st.secrets raises if no secrets file exists — fall through
        pass
    return os.environ.get("BREVO_API_KEY")


def send_email(
    to_email: str,
    to_name: str,
    subject: str,
    html_content: str,
    sender_email: str = DEFAULT_SENDER_EMAIL,
    sender_name: str = DEFAULT_SENDER_NAME,
    reply_to: Optional[str] = None,
) -> tuple[bool, str]:
    """
    Send a single transactional email via Brevo REST API.

    Returns: (success, message)
    """
    api_key = _get_api_key()
    if not api_key:
        return False, "Brevo API key not configured. Add BREVO_API_KEY to Streamlit secrets."

    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json",
    }

    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlContent": html_content,
    }

    if reply_to:
        payload["replyTo"] = {"email": reply_to}

    try:
        response = requests.post(BREVO_API_URL, json=payload, headers=headers, timeout=20)
        if response.status_code in (200, 201):
            return True, f"Email sent to {to_email}"
        # Brevo returns structured errors — surface them
        try:
            err = response.json()
            msg = err.get("message") or err.get("code") or str(err)
        except Exception:
            msg = response.text[:300]
        return False, f"Brevo error ({response.status_code}): {msg}"
    except requests.exceptions.Timeout:
        return False, "Email request timed out — check network."
    except Exception as e:
        return False, f"Email send failed: {str(e)[:200]}"


# ------------------------------------------------------------------
# Email templates — each one is a self-contained HTML email
# ------------------------------------------------------------------
BASE_STYLE = """
<style>
body { font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; background: #F5F7FA; margin: 0; padding: 20px; }
.wrap { max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.header { background: #1A3A5C; color: white; padding: 24px 28px; }
.header h1 { margin: 0; font-size: 22px; font-weight: 500; }
.header .sub { font-size: 13px; opacity: 0.85; margin-top: 4px; }
.body { padding: 28px; color: #2C2C2A; line-height: 1.65; font-size: 15px; }
.card { background: #EBF4FF; border-left: 3px solid #2B6CB0; padding: 14px 18px; border-radius: 8px; margin: 16px 0; }
.metric { display: inline-block; background: #F1EFE8; padding: 10px 16px; border-radius: 8px; margin: 4px 6px 4px 0; font-size: 13px; }
.metric strong { display: block; font-size: 20px; color: #1A3A5C; font-weight: 500; }
.footer { background: #F1EFE8; padding: 16px 28px; font-size: 12px; color: #5F5E5A; text-align: center; }
.alert { background: #FCEBEB; border-left: 3px solid #E24B4A; color: #791F1F; padding: 12px 16px; border-radius: 8px; margin: 12px 0; }
.good { background: #EAF3DE; border-left: 3px solid #639922; color: #27500A; padding: 12px 16px; border-radius: 8px; margin: 12px 0; }
</style>
"""


def send_daily_summary(
    caregiver_email: str,
    caregiver_name: str,
    patient_name: str,
    phrases_communicated: int,
    exercises_completed: int,
    exercises_total: int,
    streak_days: int,
    emotion_trend: str,
    concerning_flags: list[str],
    app_url: str = "https://speakagain.streamlit.app",
) -> tuple[bool, str]:
    """Daily handover summary for a caregiver."""

    today = datetime.now().strftime("%A, %d %B %Y")
    flags_html = ""
    if concerning_flags:
        flags_html = '<div class="alert"><strong>Please check in:</strong><br>' + \
                     "<br>".join(f"• {f}" for f in concerning_flags) + "</div>"
    else:
        flags_html = '<div class="good">No concerns flagged today. Patient communicated normally.</div>'

    html = f"""{BASE_STYLE}
<div class="wrap">
  <div class="header">
    <h1>Daily update — {patient_name}</h1>
    <div class="sub">{today}</div>
  </div>
  <div class="body">
    <p>Hello {caregiver_name},</p>
    <p>Here is today's communication and rehabilitation summary for {patient_name}.</p>
    <div>
      <div class="metric"><strong>{phrases_communicated}</strong>phrases communicated</div>
      <div class="metric"><strong>{exercises_completed}/{exercises_total}</strong>exercises done</div>
      <div class="metric"><strong>{streak_days}</strong>day streak</div>
    </div>
    <div class="card"><strong>Emotional state today:</strong><br>{emotion_trend}</div>
    {flags_html}
    <p style="margin-top: 20px;">View full progress and word recovery at<br>
      <a href="{app_url}" style="color: #2B6CB0;">{app_url}</a>
    </p>
  </div>
  <div class="footer">
    SpeakAgain — AI aphasia communication and rehabilitation aid<br>
    Built by Samuel Oluwakoya · Lagos, Nigeria · Samuel@bloomgatelaw.com
  </div>
</div>"""

    return send_email(
        to_email=caregiver_email,
        to_name=caregiver_name,
        subject=f"{patient_name}'s daily update — {phrases_communicated} phrases, {exercises_completed} exercises",
        html_content=html,
    )


def send_milestone_email(
    caregiver_email: str,
    caregiver_name: str,
    patient_name: str,
    milestone: str,
    old_score: float,
    new_score: float,
) -> tuple[bool, str]:
    """Celebration email when patient hits a milestone."""
    html = f"""{BASE_STYLE}
<div class="wrap">
  <div class="header" style="background: #27500A;">
    <h1>🎉 Milestone reached</h1>
    <div class="sub">{patient_name}'s progress</div>
  </div>
  <div class="body">
    <p>Hello {caregiver_name},</p>
    <p>Wonderful news. {patient_name} has reached a meaningful milestone in their speech rehabilitation:</p>
    <div class="good"><strong>{milestone}</strong></div>
    <div>
      <div class="metric"><strong>{old_score:.1f}</strong>previous score</div>
      <div class="metric"><strong>{new_score:.1f}</strong>current score</div>
      <div class="metric"><strong>+{new_score - old_score:.1f}</strong>improvement</div>
    </div>
    <p style="margin-top: 20px;">This kind of progress happens because of consistent daily practice and your support. Thank you for being there.</p>
  </div>
  <div class="footer">
    SpeakAgain — AI aphasia communication and rehabilitation aid<br>
    Built by Samuel Oluwakoya · Lagos, Nigeria · Samuel@bloomgatelaw.com
  </div>
</div>"""

    return send_email(
        to_email=caregiver_email,
        to_name=caregiver_name,
        subject=f"🎉 {patient_name} just reached: {milestone}",
        html_content=html,
    )


def send_concern_alert(
    caregiver_email: str,
    caregiver_name: str,
    patient_name: str,
    concern: str,
) -> tuple[bool, str]:
    """Urgent alert when patient reports distress or concerning symptoms."""
    html = f"""{BASE_STYLE}
<div class="wrap">
  <div class="header" style="background: #A32D2D;">
    <h1>Check in on {patient_name}</h1>
    <div class="sub">Important — action may be needed</div>
  </div>
  <div class="body">
    <p>Hello {caregiver_name},</p>
    <p>{patient_name} indicated something that may need your attention:</p>
    <div class="alert"><strong>{concern}</strong></div>
    <p>If this concerns you, please contact {patient_name} directly. If you believe it is a medical emergency, call local emergency services.</p>
    <p style="margin-top: 16px; font-size: 13px; color: #5F5E5A;"><em>This is an automated notification based on what {patient_name} logged in the app. SpeakAgain is not a medical diagnostic tool.</em></p>
  </div>
  <div class="footer">
    SpeakAgain — AI aphasia communication and rehabilitation aid<br>
    Built by Samuel Oluwakoya · Lagos, Nigeria · Samuel@bloomgatelaw.com
  </div>
</div>"""

    return send_email(
        to_email=caregiver_email,
        to_name=caregiver_name,
        subject=f"⚠️ Check in on {patient_name}: {concern[:40]}",
        html_content=html,
    )


def send_welcome_email(to_email: str, to_name: str, role: str = "patient") -> tuple[bool, str]:
    """Welcome email on first sign-up."""
    role_msg = (
        "You've taken a brave step. SpeakAgain is built to help you communicate today "
        "and rebuild your speech over time. Everything works at your own pace."
        if role == "patient"
        else "You're now connected as a caregiver. You'll receive daily updates and can check "
             "in on progress any time."
    )
    html = f"""{BASE_STYLE}
<div class="wrap">
  <div class="header"><h1>Welcome to SpeakAgain</h1><div class="sub">Your rehabilitation journey starts here</div></div>
  <div class="body">
    <p>Hello {to_name},</p>
    <p>{role_msg}</p>
    <div class="card">
      <strong>What happens next:</strong><br>
      • Take the 5-minute assessment to personalise your exercises<br>
      • Use Communication mode whenever you need to say something<br>
      • Do one short exercise set per day — that's enough
    </div>
    <p>Questions? Reply to this email directly.</p>
  </div>
  <div class="footer">
    SpeakAgain — AI aphasia communication and rehabilitation aid<br>
    Built by Samuel Oluwakoya · Lagos, Nigeria · Samuel@bloomgatelaw.com
  </div>
</div>"""
    return send_email(to_email, to_name, "Welcome to SpeakAgain", html)
