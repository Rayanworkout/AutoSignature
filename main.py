import os

from datetime import datetime
from dotenv import load_dotenv
from requests_html import HTMLSession

from dataclasses import dataclass

@dataclass
class Session:
    date: str
    half: str

    def __str__(self):
        return f"{self.date} {self.half}"

class Signatory:

    def __init__(self):
        load_dotenv()

        self.BASE_URL = os.getenv("BASE_URL")
        self.EMAIL = os.getenv("EMAIL")
        self.PASSWORD = os.getenv("PASSWORD")
        self.FIRST_NAME = os.getenv("FIRST_NAME")
        self.LAST_NAME = os.getenv("LAST_NAME")
        self.FORMATION_INDEX = os.getenv("FORMATION_INDEX")

        if (
            not self.EMAIL
            or not self.PASSWORD
            or not self.FORMATION_INDEX
            or not self.FIRST_NAME
            or not self.LAST_NAME
            or not self.BASE_URL
        ):
            raise ValueError("Missing data in .env file, cannot proceed")

        self.FIRST_NAME = self.FIRST_NAME.lower()
        self.LAST_NAME = self.LAST_NAME.lower()
        
        if not os.path.exists("signed_sessions.txt"):
            with open("signed_sessions.txt", "w") as f:
                f.write("")
            print("Created signed_sessions.txt")
        
        self.session = HTMLSession()

    def __session_is_signed(self, session: Session):
        with open("signed_sessions.txt", "r") as f:
            signed_sessions = f.read().splitlines()

        return str(session) in signed_sessions
    
    def __save_session(self, session: Session):
        with open("signed_sessions.txt", "a") as f:
            f.write(f"{session}\n")
        print(f"Saved session {session}")
        
        
    def __login(self):
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

        print("Logged in successfully.")

        sign_url = (
            self.BASE_URL
            + f"formation/{self.LAST_NAME}-{self.FIRST_NAME}---{self.FORMATION_INDEX}/emarger/{today}/{half}"
        )
        
        payload = {
            "sign": ""
        }

        # Get the page with the list of documents to sign
        sign_response = self.session.post(sign_url, data=payload)

        if not sign_response.ok:
            raise ValueError(
                f"Failed to sign for {today} {'morning' if half == 'am' else 'afternoon'}."
            )

        print(f"Signed for {today} {'morning' if half == 'am' else 'afternoon'}.")
        
        self.__save_session(Session(today, half))

    def run(self):
        try:
            self.__sign()
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            self.session.close()


if __name__ == "__main__":
    Signatory().run()
