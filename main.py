import os
import requests
import time
import schedule

from dataclasses import dataclass
from datetime import datetime
from dotenv import load_dotenv
from requests_html import HTMLSession
from typing import Union


@dataclass(init=True)
class Session:
    date: str
    half: str

    def __str__(self):
        return f"{self.date} {self.half}"


class Signatory:

    script_dir = os.path.dirname(os.path.abspath(__file__))
    signed_sessions_file = os.path.join(script_dir, "signed_sessions.txt")

    def __init__(self):
        load_dotenv()

        self.BASE_URL = os.getenv("BASE_URL")
        self.EMAIL = os.getenv("EMAIL")
        self.PASSWORD = os.getenv("PASSWORD")
        self.FIRST_NAME = os.getenv("FIRST_NAME")
        self.LAST_NAME = os.getenv("LAST_NAME")
        self.FORMATION_INDEX = os.getenv("FORMATION_INDEX")
        self.LESSON_DAYS_DURATION = os.getenv("LESSON_DAYS_DURATION")

        self.signature_count = 0

        # Optional
        self.TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
        self.BOT_TOKEN = os.getenv("BOT_TOKEN")

        if not all(
            (
                self.EMAIL,
                self.PASSWORD,
                self.FORMATION_INDEX,
                self.FIRST_NAME,
                self.LAST_NAME,
                self.BASE_URL,
                self.LESSON_DAYS_DURATION,
            )
        ):
            raise ValueError("Missing data in .env file, cannot proceed")

        self.FIRST_NAME = self.FIRST_NAME.lower()
        self.LAST_NAME = self.LAST_NAME.lower()

        if not self.LESSON_DAYS_DURATION.isdigit():
            raise ValueError("LESSON_DAYS_DURATION must be an integer")

        self.number_of_signatures = int(self.LESSON_DAYS_DURATION) * 2

        if not os.path.exists(Signatory.signed_sessions_file):
            with open(Signatory.signed_sessions_file, "w") as f:
                f.write("")
            print("Created signed_sessions.txt")

        self.session = HTMLSession()

    def __session_is_signed(self, session: Session):
        with open(Signatory.signed_sessions_file, "r") as f:
            signed_sessions = f.read().splitlines()

        return str(session) in signed_sessions

    def __save_session(self, session: Session):
        with open(Signatory.signed_sessions_file, "a") as f:
            f.write(f"{session}\n")

    def __login(self) -> Union[True, ValueError]:
        login_url = self.BASE_URL + "connexion"
        login_page = self.session.get(login_url)

        csrf = login_page.html.find('input[name="_csrf_token"]', first=True)

        csrf_token = csrf.attrs["value"]

        if not csrf_token:
            raise ValueError("Could not get CSRF token, aborting.")

        payload = {
            "_csrf_token": csrf_token,
            "_username": self.EMAIL,
            "_password": self.PASSWORD,
        }

        # Perform login
        response = self.session.post(login_url, data=payload)

        if not response.ok or "Mes démarches" not in response.text:
            raise ValueError("Failed to login")

        return True

    def __sign(self):
        today = datetime.now().strftime("%Y-%m-%d")
        half = "am" if datetime.now().hour < 12 else "pm"

        if self.__session_is_signed(Session(today, half)):
            print(f"Up to date !")
            return

        login = self.__login()

        if login is False:
            raise ValueError("Failed to login.")

        sign_url = (
            self.BASE_URL
            + f"formation/{self.LAST_NAME}-{self.FIRST_NAME}---{self.FORMATION_INDEX}/emarger/{today}/{half}"
        )

        payload = {"sign": ""}

        # Get the page with the list of documents to sign
        sign_response = self.session.post(sign_url, data=payload)

        if not sign_response.ok:
            raise ValueError(
                f"Failed to sign for {today} {'morning' if half == 'am' else 'afternoon'}."
            )

        print(f"Signed for {today} {'morning' if half == 'am' else 'afternoon'}.")

        self.__save_session(Session(today, half))
        self.__telegram_message()

    def __telegram_message(
        self, message: str = "Successfully signed for this session."
    ):
        requests.get(
            f"https://api.telegram.org/bot{self.BOT_TOKEN}/"
            f"sendMessage?chat_id={self.TELEGRAM_CHAT_ID}&text={message}"
        )

    def run(self):
        # Running on weekdays only
        if datetime.today().weekday() < 5:
            try:
                if self.signature_count <= self.number_of_signatures:
                    self.__sign()
                    self.signature_count += 1
                else:
                    self.__telegram_message(
                        "Successfully signed for the whole formation.\n\nPlease provide a new formation index."
                    )
                    exit(0)

            except Exception as e:
                print(f"An error occurred: {e}")
                self.__telegram_message(f"Could not sign: {e}")

            except KeyboardInterrupt:
                print("Exiting...")
                self.session.close()
                exit(0)

            finally:
                self.session.close()


if __name__ == "__main__":
    print("Starting...")
    schedule.every().day.at("11:30").do(Signatory().run)
    schedule.every().day.at("15:00").do(Signatory().run)

    while True:
        schedule.run_pending()
        time.sleep(1)
