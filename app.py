from flask import Flask, render_template, request, jsonify, redirect
import json
import os
import icalendar
from datetime import datetime

app = Flask(__name__, static_folder="static", template_folder="templates")

SETTINGS_FILE = "settings.json"
SETUP_FILE = "setup.json"
CALENDAR_FOLDER = "calendars"
REFRESH_FILE = "refresh.json"

if not os.path.exists(CALENDAR_FOLDER):
    os.makedirs(CALENDAR_FOLDER)

def load_settings():
    try:
        with open("settings.json", "r") as f:
            settings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        settings = {}

    settings.setdefault("city", "London")
    settings.setdefault("api_key", "")
    settings.setdefault("calendar_file", "")
    settings.setdefault("text_color", "#FFFFFF")
    settings.setdefault("icon_color", "#FFFFFF")

    return settings


def save_settings(data):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_setup():
    try:
        with open(SETUP_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"status": "pending"}

def save_setup(status):
    with open(SETUP_FILE, "w") as f:
        json.dump({"status": status}, f, indent=4)

def get_todays_events():
    settings = load_settings()
    ics_path = os.path.join(CALENDAR_FOLDER, settings.get("calendar_file", ""))

    if not os.path.exists(ics_path) or not settings["calendar_file"]:
        return []

    with open(ics_path, "rb") as f:
        calendar = icalendar.Calendar.from_ical(f.read())

    today = datetime.now().date()
    events = []

    for component in calendar.walk():
        if component.name == "VEVENT":
            event_summary = component.get("SUMMARY", "No Title")
            event_location = component.get("LOCATION", "No Location")
            event_start = component.get("DTSTART").dt
            if isinstance(event_start, datetime):
                event_date = event_start.date()
                event_time = event_start.strftime("%H:%M")
            else:
                event_date = event_start
                event_time = "All Day"

            if event_date == today:
                events.append({
                    "title": event_summary,
                    "time": event_time,
                    "location": event_location
                })

    return events

@app.route("/")
def index():
    settings = load_settings()
    setup_status = load_setup()
    if setup_status["status"] != "done":
        return render_template("setup.html")  
    return render_template("mirror.html", settings=settings)


@app.route("/config", methods=["GET", "POST"])
def config():
    settings = load_settings()

    if request.method == "POST":
        settings["city"] = request.form["city"]
        settings["api_key"] = request.form["api_key"]
        settings["text_color"] = request.form["text_color"]
        settings["icon_color"] = request.form["icon_color"]

        if "calendar" in request.files:
            calendar_file = request.files["calendar"]
            if calendar_file.filename.endswith(".ics"):
                filename = "calendar.ics"
                calendar_path = os.path.join(CALENDAR_FOLDER, filename)
                calendar_file.save(calendar_path)
                settings["calendar_file"] = filename

        save_settings(settings)
        save_setup("done")  
        
        with open(REFRESH_FILE, "w") as f:
            json.dump({"refresh": True}, f)

        return redirect("/")  

    return render_template("config.html", settings=settings)



@app.route("/settings")
def get_settings():
    return jsonify(load_settings())


@app.route("/calendar")
def get_calendar():
    return jsonify(get_todays_events())


@app.route("/setup-status")
def get_setup_status():
    return jsonify(load_setup())



@app.route("/refresh-mirror", methods=["POST"])
def refresh_mirror():
    with open("refresh.json", "w") as f:
        json.dump({"refresh": True}, f)

    return jsonify({"message": "Mirror will refresh"})


@app.route("/check-refresh")
def check_refresh():
    try:
        with open(REFRESH_FILE, "r") as f:
            refresh_data = json.load(f)
        if refresh_data.get("refresh"):
            with open(REFRESH_FILE, "w") as f:
                json.dump({"refresh": False}, f)
            return jsonify({"refresh": True})
    except FileNotFoundError:
        return jsonify({"refresh": False})

    return jsonify({"refresh": False})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
