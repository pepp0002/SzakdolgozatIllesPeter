import mysql.connector
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart





class ActionSaveDatabase(Action):
    def name(self) -> Text:
        return "action_save_to_database"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        
        name = tracker.get_slot("name")
        email = tracker.get_slot("email")
        description = tracker.get_slot("description")

        if not name:
            dispatcher.utter_message(text="Hiba történt. A neved nem ismert.")
            return []


        ticket_number = f"TICKET-{random.randint(1000, 9999)}"
        status = "nyitott"

        try:

            db = mysql.connector.connect(host="localhost", user="root", password="", database="adat")
            cursor = db.cursor()

            insert_query = """
            INSERT INTO adatok (name, email, description, ticket_number, status)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (name, email, description, ticket_number, status))
            db.commit()


            self.send_email_notification(name, email, description, ticket_number)

            response_text = f"Köszönjük, {name}. Az adataidat elmentettük az adatbázisba. A jegy száma: {ticket_number} és státusza: {status}."
            dispatcher.utter_message(text=response_text)

        except mysql.connector.Error as err:
            dispatcher.utter_message(text="Hiba történt az adatbázis elérése során. Kérlek, próbáld újra később.")
            print(f"Database error: {err}")

        finally:
            if cursor:
                cursor.close()
            if db:
                db.close()

        return []

    def send_email_notification(self, name, user_email, description, ticket_number):
        sender_email = "chatbotrasa1@gmail.com"
        receiver_email = "illes.pepe@gmail.com" 
        app_password = "axnx jepj bqjn adbg" 

        message = MIMEMultipart("alternative")
        message["Subject"] = f"Új hibajegy érkezett: {ticket_number}"
        message["From"] = sender_email
        message["To"] = receiver_email

        text = f"""\
        Új hibajegy érkezett.

        Jegyszám: {ticket_number}
        Felhasználónév: {name}
        Email: {user_email}
        Leírás: {description}
        """
        part = MIMEText(text, "plain")
        message.attach(part)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, receiver_email, message.as_string())


class ActionResetSlots(Action):
    def name(self):
        return "action_reset_slots"

    def run(self, dispatcher, tracker, domain):
        return [SlotSet("name", None), SlotSet("email", None), SlotSet("description", None)]


class ActionCheckTicketStatus(Action):
    def name(self) -> Text:
        return "action_check_ticket_status"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        ticket_number = tracker.get_slot("ticket_number")
        if not ticket_number:
            dispatcher.utter_message(text="Nem adtál meg jegyszámot. Kérlek, írd be a jegyszámodat.")
            return []

        try:

            db = mysql.connector.connect(
                host="localhost",
                user="root",
                password="",
                database="adat"
            )
            cursor = db.cursor()

            query = "SELECT status, admin_comments FROM adatok WHERE ticket_number = %s"
            cursor.execute(query, (ticket_number,))
            result = cursor.fetchone()

            if result:
                status, admin_comments = result
                dispatcher.utter_message(
                    text=f"A(z) {ticket_number} számú jegy állapota: {status}. Megjegyzés: {admin_comments}.")
            else:
                dispatcher.utter_message(
                    text="Sajnálom, nem találom a megadott jegyszámot az adatbázisban. Kérlek, ellenőrizd a jegyszámot.")

        except mysql.connector.Error as err:
            dispatcher.utter_message(text="Hiba történt az adatbázis elérése során. Kérlek, próbáld újra később.")
            print(f"Database error: {err}")

        finally:

            if cursor:
                cursor.close()
            if db:
                db.close()

        return []

