import requests
import threading
import random
import time
from faker import Faker
from datetime import datetime
import statistics
import socket
import http.client
from urllib.parse import urlparse
import json

BASE_URL = "http://localhost:8080/"
REGISTER_ENDPOINT = f"{BASE_URL}/users/register"
ITEM_ENDPOINT = f"{BASE_URL}/items"
DELETE_USER_ENDPOINT = f"{BASE_URL}/users"

PARSED_URL = urlparse(BASE_URL)
HOST = PARSED_URL.hostname or "localhost"
PORT = PARSED_URL.port or 80


fake = Faker()

# Save user data and tokens
users = []
tokens = []
user_ids = []
# Save item data on successful creation
item_ids = []

# Metrics
failed_transactions = 0
network_failures = 0
transaction_errors = 0
transaction_durations = []
lock = threading.Lock()

NUMBER_OF_USERS = 50
#Adjust the timeout range to simulate network conditions
MIN_TIMEOUT = 0.3
MAX_TIMEOUT = 0.6

# Register 50 users and store their JWT tokens
for _ in range(NUMBER_OF_USERS):
    user_data = {
        "email": fake.email(),
        "password": "TestPassword123!"
    }
    try:
        response = requests.post(REGISTER_ENDPOINT, json=user_data)
        response.raise_for_status()
        token = response.json().get("token")
        print(f"{response.json()}")
        if token:
            tokens.append(token)
            print(f"Registered user: {user_data['email']} with token")
        else:
            print(f"Failed to get token for {user_data['email']}")
        users.append(user_data)
        #user_id = response.json().get("id")
    except requests.RequestException as e:
        print(f"Failed to register user: {user_data['email']} - {e}")


def simulate_network_disruption_during_send():
    # Random chance to interrupt a connection during data transfer
    if random.random() < 0.3:
        print("[DEBUG] Simulating mid-transfer network interruption...")
        raise socket.error("Simulated mid-transfer network interruption")


def create_item_with_network_failure(user, token):
    global failed_transactions, network_failures, transaction_errors, transaction_durations
    conn = None  # Ensure conn is defined before use
    try:
        # Simulate random network failures during data transfer
        start_time = time.time()
        item_data = {
            "assessment": fake.word(),
            "subject": fake.word(),
            "OALevel": fake.word(),
            "specification": fake.sentence(),
            "qti": fake.word(),  # Required field for QTI
            "learningObjectives": [{"id": 1, "name": "Resolver sumas con fracciones."}],
            "curricularSkills": [{"id": 1, "name": "Resolución de problemas"}],
            "skills": [{"id": 1, "name": "Resolución de problemas"}],
            "labels": [{"id": 1, "name": "Matemática Básica"}],
            "axes": [{"id": 1, "name": "Eje Números"}],
            "processes": [
                {
                    "name": fake.word(),
                    "difficulty": round(random.uniform(0, 1), 2),
                    "discrimination": round(random.uniform(0, 1), 2),
                    "omissionRate": round(random.uniform(0, 1), 2),
                    "alternativeMetrics": [
                        {
                            "achievementRate": round(random.uniform(0, 1), 2),
                            "scoreCorrelation": round(random.uniform(0, 1), 2)
                        } for _ in range(4)
                    ]
                }
            ],
            "alternatives": [
                {"text": fake.sentence(), "isCorrect": random.choice([True, False])} for _ in range(4)
            ]
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Content-Length": str(len(json.dumps(item_data)))
        }

        # Open a direct socket connection to simulate mid-transfer failures
        conn = http.client.HTTPConnection(HOST, PORT, timeout=random.uniform(MIN_TIMEOUT, MAX_TIMEOUT))
        conn.connect()
        simulate_network_disruption_during_send()
        conn.request("POST", "/items", body=json.dumps(item_data), headers=headers)
        response = conn.getresponse()

        if response.status != 201:
            raise requests.RequestException(f"Failed with status {response.status}")
        duration = time.time() - start_time
        with lock:
            transaction_durations.append(duration)
        print(f"Created item for {user['email']} in {duration:.2f} seconds")
    except socket.error as e:
        with lock:
            network_failures += 1
            failed_transactions += 1
        print(f"Network failure for {user['email']} - {e}")
    except requests.RequestException as e:
        with lock:
            transaction_errors += 1
            failed_transactions += 1
        print(f"Failed to create item for {user['email']} - {e}")
    finally:
        if conn:
            conn.close()

def delete_all_users_and_items():
    for user in users:
        try:
            # Delete all items associated with the user
            response = requests.get(ITEM_ENDPOINT, params={"owner_email": user["email"]})
            response.raise_for_status()
            items = response.json()
            for item in items:
                item_id = item.get("id")
                delete_response = requests.delete(f"{DELETE_ITEM_ENDPOINT}/{item_id}")
                delete_response.raise_for_status()
                print(f"Deleted item {item_id} for user {user['email']}")
            # Delete the user
            delete_response = requests.delete(f"{DELETE_USER_ENDPOINT}/{user['email']}")
            delete_response.raise_for_status()
            print(f"Deleted user {user['email']}")
        except requests.RequestException as e:
            print(f"Failed to delete user {user['email']} or their items - {e}")

threads = []

# Simulate concurrent item creations with failures
for user, token in zip(users, tokens):
    thread = threading.Thread(target=create_item_with_network_failure, args=(user, token))
    threads.append(thread)
    thread.start()

# Wait for all threads to finish
for thread in threads:
    thread.join()

# Calculate stats
total_attempts = len(users)
successful_transactions = total_attempts - failed_transactions
error_rate = (failed_transactions / total_attempts) * 100 if total_attempts > 0 else 0
avg_duration = statistics.mean(transaction_durations) if transaction_durations else 0

print(f"\nTest completed.")
print(f"Total Transactions: {total_attempts}")
print(f"Successful Transactions: {successful_transactions}")
print(f"Failed Transactions: {failed_transactions}")
print(f"Network Failures: {network_failures}")
print(f"Transaction Errors: {transaction_errors}")
print(f"Average Transaction Duration: {avg_duration:.2f} seconds")
print(f"Error Rate: {error_rate:.2f}%")
