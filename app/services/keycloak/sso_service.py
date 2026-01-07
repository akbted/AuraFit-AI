import requests
from app.config.settings import setting
import logging
from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/sso_service.log"), # Writes to a file
        logging.StreamHandler()         # Also prints to console
    ]
)

class KeyCloakClient:
    def __init__(self, target_realm = "master"):
        self.keycloakurl = setting.KEYCLOAK_URL
        self.keycloakusername = setting.KEYCLOAK_ADMIN_USERNAME
        self.keycloakpassword = setting.KEYCLOAK_ADMIN_PASSWORD
        logging.debug(f"Logging URL, USERNAME - {self.keycloakurl, self.keycloakusername}")
        self.client = KeycloakAdmin(
                server_url=self.keycloakurl,
                username=self.keycloakusername,
                password=self.keycloakpassword,
                realm_name="master",
                user_realm_name="master",
                verify=True
            )
        
        if target_realm != "master":
            self.client.realm_name = target_realm

    def create_realm(self, realm_name):
        try:
            existing_realms = self.client.get_realms()
            if any(r['realm'] == realm_name for r in existing_realms):
                logging.info(f"Realm {realm_name} already exists.")
            else:
                self.client.create_realm(
                    payload={
                        "realm": realm_name,
                        "enabled": True,
                        "displayName": realm_name
                    }
                )
            logging.info(f"Realm '{realm_name}' created successfully.")
            self.client.realm_name = realm_name
        except Exception as e:
            logging.error(f"Failed to create realm {realm_name}: {e}")

    def create_client(self, client_id_name,):
        try:
            new_client_id = self.client.create_client(
                payload={
                    "clientID" : client_id_name,
                    "enabled" : True,
                    "protocol" : "openid-connect",
                    "publicClient" : False, 
                    "directAccessGrantsEnabled" : True,
                    "redirectUris": ["http://localhost:5000/*"]
                }
            )
            logging.info(f"Client '{client_id_name}' created successfully.")
        except KeycloakError as e:
            if e.response_code == 409:
                logging.info(f"Client '{client_id_name}' already exists.")
            else:
                logging.info(f"Client creation failed (might already exist): {e}")

    def create_roles(self, client_id_name: str, roles_dict: dict):
        try:
            client_uuid = self.client.get_client_id(client_id=client_id_name)
            self.client.create_client_role(client_role_id=client_uuid, payload = {"name" : roles_dict.get("name", ""), "description" : roles_dict.get("description", "")
            })
            logging.info(f"Client role created for client '{client_id_name}'.")
        except KeycloakError as e:
            logging.info(f"Client role creation skipped: {e}")


class KeyCloakUserManagement:
    def __init__(self, target_realm = "master"):
        self.keycloakuri = setting.KEYCLOAK_URL
        self.keycloakusername = setting.KEYCLOAK_ADMIN_USERNAME
        self.keycloakpassword = setting.KEYCLOAK_ADMIN_PASSWORD

        self.client = KeycloakAdmin(
            server_url=self.keycloakurl,
            username=self.keycloakusername,
            password=self.keycloakpassword,
            realm_name=target_realm, 
            user_realm_name="master", 
            verify=True
        )
        
    def create_user(self, new_user_payload: dict):
            try:
                user_id = self.client.create_user(new_user_payload, exist_ok=True)
                logging.info(f"User '{new_user_payload.get('username')}' created/found with ID: {user_id}")
                return user_id
            except KeycloakError as e:
                logging.error(f"Failed to create user: {e}")
                try:
                    user_id = self.client.get_user_id(new_user_payload['username'])
                    return user_id
                except:
                    return None

    def assign_client_role(self, user_id: str, client_id_name: str, role_name: str):
        """
        Assigns a specific client role to a user.
        """
        try:
            # 1. Get Client Internal UUID
            client_uuid = self.client.get_client_id(client_id_name)
            if not client_uuid:
                logging.error(f"Client '{client_id_name}' not found.")
                return

            # 2. Get Role Definition
            # We must fetch the full role object to pass it to assign_client_role
            role_to_assign = self.client.get_client_role(
                client_id=client_uuid, 
                role_name=role_name
            )

            # 3. Assign Role to User
            self.client.assign_client_role(
                client_id=client_uuid, 
                user_id=user_id, 
                roles=[role_to_assign]
            )
            logging.info(f"Assigned role '{role_name}' to user {user_id}.")
            
        except KeycloakError as e:
            logging.error(f"Failed to assign role '{role_name}': {e}")

    
if __name__ == "__main__":
    keycloakclient = KeyCloakClient()
    admintoken = keycloakclient.get_admin_token()
    print(admintoken)