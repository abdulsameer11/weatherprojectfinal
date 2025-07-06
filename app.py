from flask import Flask, render_template, request, redirect, session, jsonify
import requests
import random
from datetime import datetime
from collections import defaultdict
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "secret-key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///weather_users.db'
db = SQLAlchemy(app)

# ✅ Your OpenWeatherMap API Key
API_KEY = "9f7e6581274d8755164e48c3876c4386"

# ✅ Models
class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100))
    city = db.Column(db.String(100))
    searched_at = db.Column(db.DateTime, default=datetime.utcnow)

# ✅ Dummy OTP Generator
def generate_dummy_otp():
    return str(random.randint(100000, 999999))

# ✅ Login Page
@app.route('/')
def login():
    return render_template('login.html')

# ✅ Send OTP
@app.route('/send_otp', methods=['POST'])
def send_otp():
    name = request.form.get('name')
    email = request.form.get('email')
    if not name or not email:
        return redirect('/')

    session['name'] = name
    session['email'] = email
    otp = generate_dummy_otp()
    session['otp'] = otp

    return f"<script>alert('Your OTP is: {otp}'); window.location.href='/otp';</script>"

# ✅ OTP Page
@app.route('/otp')
def otp():
    return render_template('otp.html')

# ✅ Verify OTP
@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    user_otp = request.form.get('otp')
    if user_otp == session.get('otp'):
        return redirect('/home')
    return "<script>alert('❌ Invalid OTP'); window.location.href='/';</script>"

# ✅ Home Page
@app.route('/home')
def home():
    name = session.get('name', 'User')
    return render_template('home.html', name=name)

# ✅ Weather Page
@app.route('/weather')
def weather():
    return render_template('weather.html')

# ✅ Current Weather API
@app.route('/weather_api')
def get_current_weather():
    city = request.args.get('city')
    if not city:
        return jsonify({"error": "City not provided"}), 400

    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
    res = requests.get(url).json()

    if "main" not in res:
        return jsonify({"error": "City not found"}), 404

    # ✅ Save search to history if user is logged in
    if 'email' in session:
        history = SearchHistory(email=session['email'], city=city)
        db.session.add(history)
        db.session.commit()

    return jsonify({
        "city": res["name"],
        "temperature": {
            "celsius": f"{res['main']['temp']:.1f} °C",
            "fahrenheit": f"{(res['main']['temp'] * 9/5 + 32):.1f} °F",
            "kelvin": f"{(res['main']['temp'] + 273.15):.1f} K"
        },
        "humidity": f"{res['main']['humidity']}%",
        "weather": res['weather'][0]['description'].title(),
        "wind_speed": f"{res['wind']['speed']} m/s"
    })

# ✅ Hourly Forecast
@app.route('/forecast')
def forecast():
    city = request.args.get('city')
    if not city:
        return jsonify({"error": "City not provided"})

    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units=metric"
    res = requests.get(url).json()

    if "list" not in res:
        return jsonify({"error": "Forecast not found"}), 404

    data = []
    for entry in res["list"][:5]:
        dt = datetime.strptime(entry['dt_txt'], "%Y-%m-%d %H:%M:%S")
        data.append({
            "datetime": dt.strftime("%I:%M %p"),
            "temperature": f"{entry['main']['temp']:.1f} °C",
            "weather": entry['weather'][0]['description'].title()
        })
    return jsonify({"forecast": data})

# ✅ Daily Forecast (5 Days) — Fixed for Free Plan
@app.route('/daily_forecast')
def daily_forecast():
    city = request.args.get('city')
    if not city:
        return jsonify({"error": "City not provided"})

    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units=metric"
    res = requests.get(url).json()

    if "list" not in res:
        return jsonify({"error": "Forecast not available"})

    grouped = defaultdict(list)
    for entry in res["list"]:
        date = entry['dt_txt'].split(" ")[0]
        grouped[date].append(entry)

    result = []
    for i, (date, entries) in enumerate(grouped.items()):
        temps = [e['main']['temp'] for e in entries]
        weather = entries[0]['weather'][0]['description']
        result.append({
            "date": datetime.strptime(date, "%Y-%m-%d").strftime("%A, %d %b"),
            "min_temp": f"{min(temps):.1f} °C",
            "max_temp": f"{max(temps):.1f} °C",
            "weather": weather.title()
        })
        if i == 5: break  # limit to 5 days

    return jsonify({"forecast": result})

# ✅ Pages
@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/profile')
def profile():
    if 'email' not in session:
        return redirect('/')
    history = SearchHistory.query.filter_by(email=session['email']).order_by(SearchHistory.searched_at.desc()).all()
    return render_template('profile.html', name=session.get('name'), email=session.get('email'), history=history)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
