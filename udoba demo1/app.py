
import csv
import os
import smtplib
import ssl

from datetime import datetime, timezone, timedelta
from email.message import EmailMessage

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_file,
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)


# --------------------------------------------------
# APPLICATION CONFIGURATION
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LOGIN_REPORT_FILE = os.path.join(
    BASE_DIR,
    "login_activity.csv"
)

app = Flask(__name__)

# Render should have BGFIBank_SECRET configured
# in its Environment settings.
SECRET_KEY = os.environ.get("BGFIBank_SECRET")

if os.environ.get("RENDER") and not SECRET_KEY:
    raise RuntimeError(
        "BGFIBank_SECRET is missing from Render environment variables."
    )

app.secret_key = SECRET_KEY or "local-development-only-secret"

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=bool(os.environ.get("RENDER")),
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
)


# --------------------------------------------------
# BGFIBank LOGIN DETAILS
# --------------------------------------------------

EMAIL = "shinsuzuki@bgfibank.com"

PASSWORD_HASH = generate_password_hash(
    "suzuku1234"
)


# --------------------------------------------------
# EMAIL CONFIGURATION
# --------------------------------------------------

def get_mail_settings():
    """Read email settings from the operating environment."""

    username = os.environ.get("MAIL_USERNAME")
    password = os.environ.get("MAIL_PASSWORD")

    if not username or not password:
        return None

    return {
        "username": username,
        "password": password,
        "server": os.environ.get(
            "MAIL_SERVER",
            "smtp.gmail.com"
        ),
        "port": int(
            os.environ.get("MAIL_PORT", "587")
        ),
    }


# --------------------------------------------------
# LOGIN ACTIVITY REPORT
# --------------------------------------------------

def send_login_report_email():
    """Email the login activity CSV without storing passwords."""

    if not os.path.isfile(LOGIN_REPORT_FILE):
        app.logger.warning(
            "Login activity report does not exist."
        )
        return False

    try:
        settings = get_mail_settings()

        if not settings:
            app.logger.warning(
                "Email settings are not configured. "
                "Login activity remains available in the CSV report."
            )
            return False

        message = EmailMessage()

        message["Subject"] = "BGFIBank - Login Activity Report"
        message["From"] = settings["username"]
        message["To"] = "udobadwaynea@gmail.com"

        message.set_content(
            "Attached is the latest BGFIBank login activity report. "
            "The report contains login activity but never contains passwords."
        )

        with open(LOGIN_REPORT_FILE, "rb") as report:
            message.add_attachment(
                report.read(),
                maintype="text",
                subtype="csv",
                filename="login_activity.csv"
            )

        with smtplib.SMTP(
            settings["server"],
            settings["port"],
            timeout=20
        ) as server:

            server.starttls(
                context=ssl.create_default_context()
            )

            server.login(
                settings["username"],
                settings["password"]
            )

            server.send_message(message)

        app.logger.info(
            "Login activity report emailed successfully."
        )

        return True

    except Exception:
        app.logger.exception(
            "Could not email the login activity report."
        )
        return False


# --------------------------------------------------
# SAVE LOGIN ACTIVITY
# --------------------------------------------------

def save_login_activity(email, result):
    """Save safe login details. Never save passwords."""

    activity = {
        "time_utc": datetime.now(
            timezone.utc
        ).isoformat(),

        "email_entered": email,
        "result": result,
        "client_ip": request.remote_addr,
        "client_port": request.environ.get("REMOTE_PORT"),
        "server_port": request.environ.get("SERVER_PORT"),
    }

    fieldnames = [
        "time_utc",
        "email_entered",
        "result",
        "client_ip",
        "client_port",
        "server_port",
    ]

    try:
        file_exists = os.path.isfile(LOGIN_REPORT_FILE)

        with open(
            LOGIN_REPORT_FILE,
            "a",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames
            )

            if not file_exists or os.path.getsize(
                LOGIN_REPORT_FILE
            ) == 0:
                writer.writeheader()

            writer.writerow(activity)

        app.logger.info(
            "Login activity recorded: %s - %s",
            email,
            result
        )

        # Preserve the existing email-report behaviour.
        send_login_report_email()

    except Exception:
        app.logger.exception(
            "Could not save login activity."
        )


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

@app.route("/")
def dashboard():

    if not session.get("logged_in"):
        return redirect(url_for("login"))

    return render_template("index.html")


# --------------------------------------------------
# PROFILE SETTINGS
# --------------------------------------------------

@app.route("/profile-settings", methods=["GET", "POST"])
def profile_settings():

    if not session.get("logged_in"):
        return redirect(url_for("login"))

    message = ""

    if request.method == "POST":

        form_type = request.form.get(
            "form_type",
            ""
        )

        if form_type == "profile":
            message = (
                "Profile settings saved for this session."
            )

        elif form_type == "notifications":
            message = (
                "Notification preferences updated."
            )

        elif form_type == "security":
            message = (
                "Password was changed and "
                "two-step verification was enabled."
            )

    return render_template(
        "profile_settings.html",
        message=message
    )


# --------------------------------------------------
# TRANSFER
# --------------------------------------------------

@app.route("/transfer")
def transfer():

    if not session.get("logged_in"):
        return redirect(url_for("login"))

    return render_template("transfer.html")


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.route("/logout", methods=["GET", "POST"])
def logout():

    session.clear()

    return redirect(url_for("login"))


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    error = ""

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        login_success = (
            email == EMAIL.strip().lower()
            and check_password_hash(
                PASSWORD_HASH,
                password
            )
        )

        # Record activity without recording the password.
        save_login_activity(
            email,
            "success" if login_success else "failure"
        )

        if login_success:

            session.clear()
            session["logged_in"] = True
            session.permanent = True

            return redirect(url_for("dashboard"))

        error = (
            "Incorrect email or password. Please try again."
        )

    return render_template(
        "login.html",
        error=error
    )


# --------------------------------------------------
# CONTACT SUPPORT
# --------------------------------------------------

@app.route("/contact", methods=["GET", "POST"])
def contact():

    success = None
    error = None

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        sender_email = request.form.get(
            "email",
            ""
        ).strip()

        user_message = request.form.get(
            "message",
            ""
        ).strip()

        if not name or not sender_email or not user_message:

            error = "Please complete all fields."

        elif (
            len(name) > 100
            or len(sender_email) > 254
            or len(user_message) > 5000
            or "\n" in sender_email
            or "\r" in sender_email
        ):

            error = "One or more fields are invalid or too long."

        else:

            try:
                settings = get_mail_settings()

                if not settings:
                    raise RuntimeError(
                        "Email service is not configured."
                    )

                message = EmailMessage()

                message["Subject"] = (
                    "BGFI BANK - Contact Support"
                )

                message["From"] = settings["username"]
                message["To"] = settings["username"]
                message["Reply-To"] = sender_email

                message.set_content(
                    f"New support message\n\n"
                    f"Name: {name}\n"
                    f"Email: {sender_email}\n\n"
                    f"Message:\n{user_message}"
                )

                with smtplib.SMTP(
                    settings["server"],
                    settings["port"],
                    timeout=20
                ) as server:

                    server.starttls(
                        context=ssl.create_default_context()
                    )

                    server.login(
                        settings["username"],
                        settings["password"]
                    )

                    server.send_message(message)

                success = (
                    "Your message has been sent successfully!"
                )

            except Exception:

                app.logger.exception(
                    "Could not send contact support message."
                )

                error = (
                    "Sorry, your message could not be sent. "
                    "Please try again."
                )

    return render_template(
        "contact.html",
        success=success,
        error=error
    )


# --------------------------------------------------
# DOWNLOAD LOGIN REPORT
# --------------------------------------------------

@app.route("/download-login-report")
def download_login_report():

    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if not os.path.isfile(LOGIN_REPORT_FILE):
        return (
            "No login activity report exists yet.",
            404
        )

    return send_file(
        LOGIN_REPORT_FILE,
        as_attachment=True,
        download_name="login_activity.csv",
        mimetype="text/csv"
    )


# --------------------------------------------------
# APPLICATION START
# --------------------------------------------------

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
