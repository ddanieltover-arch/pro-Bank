import smtplib
import ssl

def test_smtp():
    host = "server596.iseencloud.net"
    port = 465
    user = "refunds@my-probank.com"
    password = "C=-E{Jo3dIKTT$y="

    context = ssl.create_default_context()

    try:
        print(f"Connecting to {host}:{port} via SSL...")
        with smtplib.SMTP_SSL(host, port, context=context, timeout=10) as server:
            print("Connected. Logging in...")
            server.login(user, password)
            print("Login successful.")
            
            # Send a simple test email
            sender = user
            receiver = user
            message = f"Subject: SMTP Test\n\nThis is a test email from the ProBank debug script."
            server.sendmail(sender, receiver, message)
            print("Test email sent successully.")
            
    except Exception as e:
        print(f"SMTP Test Failed: {str(e)}")

if __name__ == "__main__":
    test_smtp()
