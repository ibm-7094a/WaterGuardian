import serial
import json
import requests
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ============================================================
#  Water Quality Monitor — Arduino → FastAPI → SMS Alert
#
#  When "is_safe" == False, this script sends a text alert
#  using an email-to-SMS gateway (via your email provider).
#
#  📱 Common U.S. SMS Gateways:
#  - AT&T:        number@txt.att.net
#  - Verizon:     number@vtext.com
#  - T-Mobile:    number@tmomail.net
#  - Sprint:      number@messaging.sprintpcs.com
#  - Boost:       number@myboostmobile.com
#  - Cricket:     number@sms.cricketwireless.net
#  - MetroPCS:    number@mymetropcs.com
#  - U.S. Cellular: number@email.uscc.net
#
#  Example:
#      RECEIVER_EMAIL = "1234567890@vtext.com"   # Verizon SMS
# ============================================================

API_URL = "http://localhost:8000/sensor_data"
SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200
# weird ahh baud rate

# Email / SMS settings
SENDER_EMAIL = "youremail@provider.com"
SENDER_PASSWORD = "xxxxxxxxxxxxxxxx"  # App-specific password (for Gmail)
RECEIVER_EMAIL = "verizonnumber@vtext.com"  # e.g. 1234567890@vtext.com

# ===== FUNCTIONS =====
def send_email_alert(subject, body):
    """Send a text/email alert."""
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("📨 Alert sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send alert: {e}")

def main():
    print("🔌 Connecting to Arduino on", SERIAL_PORT)
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
        time.sleep(2)
        print("✅ Connected. Listening for data...\n")
    except Exception as e:
        print(f"❌ Could not open {SERIAL_PORT}: {e}")
        return

    while True:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if not line:
                    continue

                print(f"📥 Raw from Arduino: {line}")

                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    print("⚠️ Invalid JSON, skipping line.")
                    continue

                if "TDS" not in data or "temperature" not in data:
                    print("⚠️ Missing fields, skipping.")
                    continue

                try:
                    response = requests.post(API_URL, json=data)
                    if response.status_code == 200:
                        result = response.json()
                        print(f"✅ Sent to API | Reading #{result['id']} | Safe: {result['is_safe']}")

                        # 🚨 ALERT if unsafe
                        if not result['is_safe']:
                            subject = "⚠️ Water Quality Alert!"
                            body = (
                                f"Unsafe reading detected:\n\n"
                                f"TDS: {data['TDS']}\n"
                                f"Temperature: {data['temperature']}°C\n\n"
                                f"Please check your water system immediately."
                            )
                            send_email_alert(subject, body)
                    else:
                        print(f"⚠️ API error {response.status_code}: {response.text}")
                except requests.RequestException as e:
                    print(f"❌ Failed to send data: {e}")

        except KeyboardInterrupt:
            print("\n🛑 Stopped by user.")
            break
        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(1)

    ser.close()
    print("🔌 Serial connection closed.")

if __name__ == "__main__":
    main()
