import pandas as pd
import smtplib
from email.message import EmailMessage
import streamlit as st
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def send_automated_emails(df, sender_email, sender_password, cc_email, log_container):
    """
    Analyzes user status from a DataFrame and sends emails based on a specific logic.
    - Connects to Gmail's SMTP server using SMTP_SSL for security.
    - Uses the EmailMessage class for a clean email structure.
    - Contains logic to check download and registration status by site.
    - Logs output to a Streamlit container.
    """
    try:
        # Establish a secure connection with the SMTP server
        log_container.info("Establishing secure connection with SMTP server...")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_password)
            log_container.success("Login successful.")

            # Group data by 'Site Number' to process each site individually
            for site_number, site_df in df.groupby('Site Number'):
                log_container.markdown(f"--- \n**Processing Site: {site_number}**")

                # LOGIC 1: If anyone in a site has DOWNLOAD = YES, skip the entire site.
                # Corrected line: 'str.upper()' is a vectorized operation on the Series,
                # which is the correct way to handle this in pandas.
                if 'YES' in site_df['DOWNLOAD'].astype(str).str.upper().unique():
                    log_container.warning(f"Site {site_number}: At least one user has downloaded. No emails will be sent.")
                    continue

                # --- Proceed since no one in the site has downloaded ---
                is_anyone_registered = 'CREATION SUCCESSFUL' in site_df['SDA Status'].unique()

                for index, row in site_df.iterrows():
                    recipient_email = row['Email']
                    
                    msg = EmailMessage()
                    msg['From'] = sender_email
                    msg['To'] = recipient_email
                    if cc_email:
                        msg['Cc'] = cc_email

                    # LOGIC 2: If some are registered, tailor emails based on status.
                    if is_anyone_registered:
                        if row['SDA Status'] == 'CREATION SUCCESSFUL':
                            msg['Subject'] = 'Reminder: Please Download Your File'
                            msg.set_content("Dear User,\n\nThis is a friendly reminder to please download the file associated with your account.\n\nThank you,\nAutomation Team")
                        else:
                             msg['Subject'] = 'Action Required: Please Complete Your Registration'
                             msg.set_content("Dear User,\n\nOur records show you have not yet completed registration. Please register to gain access.\n\nThank you,\nAutomation Team")
                    
                    # LOGIC 3: If no one is registered, send "Please register" to everyone.
                    else:
                        msg['Subject'] = 'Action Required: Please Register'
                        msg.set_content("Dear User,\n\nThis email is to invite you to register for our platform. Please complete your registration at your earliest convenience.\n\nThank you,\nAutomation Team")

                    smtp.send_message(msg)
                    log_container.success(f"Email sent to: {recipient_email} | Subject: '{msg['Subject']}'")

    except smtplib.SMTPAuthenticationError:
        log_container.error("[AUTHENTICATION ERROR] Login failed. Please verify your credentials and ensure you are using a valid App Password.")
    except Exception as e:
        log_container.error(f"[UNEXPECTED ERROR] An error occurred: {e}")
    finally:
        st.balloons()
        log_container.info("--- Email sending process finished ---")

## starts from here

# --- Streamlit App Interface ---

st.set_page_config(layout="wide")
st.title("Splunk report notifier")

# --- Get credentials from environment variables ---
sender_email = os.getenv("SENDER_EMAIL")
sender_password = os.getenv("SENDER_PASSWORD")

if not sender_email or not sender_password:
    st.error("Email credentials not found. Please create a `.env` file with `SENDER_EMAIL` and `SENDER_PASSWORD`.")
else:
    st.info("Email credentials loaded successfully from `.env` file.")

# --- Sidebar for Configuration ---
with st.sidebar:
    st.header("⚙️ Configuration")
    st.info("Sender email and app password are read from the `.env` file.")
    cc_email = st.text_input("CC Email Address (optional, comma-separated)")
    st.markdown("---")
    

# --- Main Page for File Upload and Execution ---
st.header("1. Upload Your Data File")
uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=['csv', 'xlsx'])

if uploaded_file:
    try:
        # Read the uploaded file into a DataFrame
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.header("2. Preview Your Data")
        st.dataframe(df.head())

        # Verify that all necessary columns are present
        required_columns = ['Site Number', 'DOWNLOAD', 'SDA Status', 'Email']
        missing_cols = [col for col in required_columns if col not in df.columns]

        if missing_cols:
            st.error(f"The uploaded file is missing required columns: **{', '.join(missing_cols)}**")
        else:
            st.header("3. Send Emails")
            if st.button("🚀 Process and Send Emails"):
                # --- Execution Logic ---
                log_container = st.container()
                if not sender_email or not sender_password:
                    log_container.error("Sender email or password is not set in the `.env` file.")
                else:
                    send_automated_emails(df, sender_email, sender_password, cc_email, log_container)

    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")
