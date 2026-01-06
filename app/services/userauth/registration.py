import psycopg2
import logging
from app.database.db_init import DBManger
from app.services.keycloak.sso_service import KeyCloakClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/sso_service.log"), # Writes to a file
        logging.StreamHandler()         # Also prints to console
    ]
)

class Registration:
    def __init__(self):
        self.connection = DBManger().connection

    def create_user(self, user_details: dict):
        try:
            email = user_details.get("email", "")
            mobile = user_details.get("mobile", "")
            password_hash = user_details.get("password", "")
            first_name = user_details.get("first_name", "")
            last_name = user_details.get("last_name", "")
            date_of_birth = user_details.get("date_of_birth", "")
            gender = user_details.get("gender", "")
            weight_kg = user_details.get("weight_kg", "")
            height_cm = user_details.get("height_cm", "")
            blood_group = user_details.get("blood_group", "")
            city = user_details.get("city", "") 
            state = user_details.get("state", "")
            country = user_details.get("country", "")

            if not (email, password_hash, first_name, last_name, date_of_birth, gender):
                raise ValueError(f"Incomplete Form, Registration Failed")
            
            # Create User Details in Keycloak
            
            


        except Exception as e:
            logging.error(f"Failed to create user: {e}")

    

