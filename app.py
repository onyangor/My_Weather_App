import streamlit as st
import requests
from streamlit_lottie import st_lottie
from datetime import datetime
import pandas as pd
import pydeck as pdk
import matplotlib.pyplot as plt
import os

# ================= CONFIG =================
WEATHER_API_KEY = "508b0a659c5748acbb7180136261602"
BASE_URL = "https://api.weatherapi.com/v1/forecast.json"

# ⚠️ FOR SUBMISSION ONLY (NOT RECOMMENDED LONG TERM)
OPENAI_API_KEY = "PUT-YOUR-KEY-HERE"   # you may paste it here if required
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

try:
    import openai
    OPENAI_AVAILABLE = True
except:
    OPENAI_AVAILABLE = False

# ================= PAGE =================
st.set_page_config(
    page_title="Creative Weather Dashboard",
    page_icon="🌦️",
    layout="wide"
)

# ================= STATE =================
st.session_state.setdefault("theme", "light")
st.session_state.setdefault("favorites", [])

# ================= THEME TOGGLE =================
dark = st.toggle("🌗 Dark Mode", value=st.session_state.theme == "dark")
st.session_state.theme = "dark" if dark else "light"

# ================= SAFE STYLING =================
st.markdown(f"""
<style>
.stApp {{
    background: {"linear-gradient(180deg,#0f2027,#203a43,#2c5364)" if dark else "linear-gradient(180deg,#a0c4ff,#ffffff)"};
    color: {"white" if dark else "black"};
}}

.temp-bar {{
    height: 16px;
    border-radius: 10px;
    background: linear-gradient(90deg,#00f,#0ff,#0f0,#ff0,#f00);
    animation: pulse 2s infinite alternate;
}}

@keyframes pulse {{
    from {{opacity:0.7}}
    to {{opacity:1}}
}}
</style>
""", unsafe_allow_html=True)

# ================= TITLE =================
st.title("🌦️ Ultimate Creative Weather Dashboard")

# ================= GEO =================
try:
    city_default = requests.get("https://ipapi.co/json/", timeout=4).json().get("city", "")
except:
    city_default = ""

city = st.text_input("🌍 Enter City", value=city_default)

# ================= FAVORITES =================
if city and st.button("⭐ Add to Favorites"):
    if city not in st.session_state.favorites:
        st.session_state.favorites.append(city)

if st.session_state.favorites:
    st.markdown("### ⭐ Favorites")
    st.write(", ".join(st.session_state.favorites))

# ================= WEATHER =================
@st.cache_data(ttl=900)
def fetch_weather(city):
    r = requests.get(BASE_URL, params={
        "key": WEATHER_API_KEY,
        "q": city,
        "days": 7
    })
    return r.json() if r.status_code == 200 else None

# ================= LOTTIE SAFE =================
def load_lottie(url):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200 and r.text.strip().startswith("{"):
            return r.json()
    except:
        pass
    return None

# ================= AI SAFE =================
def ai_weather_advice(location, cur):
    if not OPENAI_AVAILABLE or not OPENAI_API_KEY:
        return "🤖 AI disabled."

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": f"Give friendly weather advice for {location}. "
                           f"It is {cur['temp_c']}°C and {cur['condition']['text']}."
            }],
            max_tokens=80
        )
        return response.choices[0].message.content
    except:
        return "🤖 AI unavailable right now."

# ================= MAIN =================
if st.button("🔍 Get Weather") and city:
    data = fetch_weather(city)

    if not data:
        st.error("Weather fetch failed.")
        st.stop()

    loc = data["location"]
    cur = data["current"]
    forecast = data["forecast"]["forecastday"]

    st.success(f"📍 {loc['name']}, {loc['country']}")

    st.metric("🌡️ Temperature", f"{cur['temp_c']}°C")
    st.markdown('<div class="temp-bar"></div>', unsafe_allow_html=True)
    st.image(f"https:{cur['condition']['icon']}", width=80)

    # ===== Animation =====
    cond = cur["condition"]["text"].lower()
    animation = None

    if "rain" in cond:
        animation = load_lottie("https://assets2.lottiefiles.com/packages/lf20_rpC1Rd.json")
    elif "snow" in cond:
        animation = load_lottie("https://assets10.lottiefiles.com/packages/lf20_jmBauI.json")
    elif "sun" in cond or "clear" in cond:
        animation = load_lottie("https://assets9.lottiefiles.com/packages/lf20_qp1q7mct.json")

    if animation:
        st_lottie(animation, height=200)

    # ===== AI =====
    st.subheader("🤖 AI Weather Advice")
    st.info(ai_weather_advice(loc["name"], cur))

    # ===== MAP =====
    st.pydeck_chart(pdk.Deck(
        initial_view_state=pdk.ViewState(
            latitude=loc["lat"],
            longitude=loc["lon"],
            zoom=7
        ),
        layers=[pdk.Layer(
            "ScatterplotLayer",
            data=pd.DataFrame({"lat":[loc["lat"]],"lon":[loc["lon"]]}),
            get_position='[lon, lat]',
            get_radius=15000,
            get_fill_color=[255, 80, 80]
        )]
    ))

    # ===== HOURLY =====
    st.subheader("📊 Hourly Temperature")
    hours = forecast[0]["hour"]
    times = [h["time"].split(" ")[1] for h in hours]
    temps = [h["temp_c"] for h in hours]

    plt.figure(figsize=(10,4))
    plt.plot(times, temps)
    plt.xticks(rotation=45)
    st.pyplot(plt)

    # ===== FORECAST =====
    st.subheader("📅 7-Day Forecast")
    for d in forecast:
        cols = st.columns(4)
        cols[0].write(datetime.strptime(d["date"], "%Y-%m-%d").strftime("%A"))
        cols[1].metric("Max", f"{d['day']['maxtemp_c']}°C")
        cols[2].metric("Min", f"{d['day']['mintemp_c']}°C")
        cols[3].write(d["day"]["condition"]["text"])
