import os

from datetime import datetime
from dotenv import load_dotenv
from requests_html import HTMLSession


class Signatory:

    BASE_URL = "https://moncompte.dawan.fr/"

    def __init__(self):
        load_dotenv()

        self.EMAIL = os.getenv("EMAIL")
        self.PASSWORD = os.getenv("PASSWORD")
        self.FIRST_NAME = os.getenv("FIRST_NAME")
        self.LAST_NAME = os.getenv("LAST_NAME")
        self.FORMATION_INDEX = os.getenv("FORMATION_INDEX")

        if not self.EMAIL or not self.PASSWORD:
            raise ValueError("Missing email or password in .env file")

        self.session = HTMLSession()

    def __login(self):
        login_url = Signatory.BASE_URL + "connexion"
        login_page = self.session.get(login_url)

        csrf = login_page.html.find('input[name="_csrf_token"]', first=True)

        csrf_token = csrf.attrs["value"]

        if not csrf_token:
            raise ValueError("Could not get CSRF token, aborting.")

        form_data = {
            "_csrf_token": csrf_token,
            "_username": self.EMAIL,
            "_password": self.PASSWORD,
        }

        # Perform login
        response = self.session.post(login_url, data=form_data)

        if not response.ok or "Mes démarches" not in response.text:
            raise ValueError("Failed to login")

        return True

    def __sign(self):

        login = self.__login()

        if login is False:
            raise ValueError("Failed to login")

        print("Logged in successfully")

        today = datetime.now().strftime("%Y-%m-%d")
        half = "am" if datetime.now().hour < 12 else "pm"

        sign_url = (
            Signatory.BASE_URL
            + f"formation/{self.LAST_NAME}-{self.FIRST_NAME}---{self.FORMATION_INDEX}/emarger/{today}/{half}"
        )

        # Get the page with the list of documents to sign
        sign_response = self.session.post(sign_url)

        if not sign_response.ok:
            raise ValueError(
                f"Failed to sign for {today} {'morning' if half == 'am' else 'afternoon'}"
            )

        print(f"Signed for {today} {'morning' if half == 'am' else 'afternoon'}")

    def run(self):
        try:
            self.__sign()
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            self.session.close()


if __name__ == "__main__":
    Signatory().run()
