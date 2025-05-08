import requests
import threading
import random
import time
from faker import Faker
from datetime import datetime
import statistics
import socket

BASE_URL = "http://localhost:8080/"
REGISTER_ENDPOINT = f"{BASE_URL}/users/register"
ITEM_ENDPOINT = f"{BASE_URL}/items"

fake = Faker()
users = []
tokens = []

# Métricas de rendimiento
failed_transactions = 0
transaction_durations = []
network_failures = 0
transaction_errors = 0
lock = threading.Lock()

NUMBER_OF_USERS = 200

# Register users and store their JWT tokens
for _ in range(NUMBER_OF_USERS):
    user_data = {
        "email": fake.email(),
        "password": "TestPassword123!"
    }
    try:
        response = requests.post(REGISTER_ENDPOINT, json=user_data)
        response.raise_for_status()
        token = response.json().get("token")
        if token:
            tokens.append(token)
            print(f"Registered user: {user_data['email']} with token")
        else:
            print(f"Failed to get token for {user_data['email']}")
        users.append(user_data)
    except requests.RequestException as e:
        print(f"Failed to register user: {user_data['email']} - {e}")


def create_item_with_network_failure(user, token):
    global failed_transactions, network_failures, transaction_errors, transaction_durations
    try:
        # Simulate random network failures
        start_time = time.time()

        # Simulate a network failure with a 30% chance
        if random.random() < 0.3:
            with lock:
                network_failures += 1
            raise requests.ConnectionError("Simulated network failure")
        
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
            "Authorization": f"Bearer {token}"
        }
        response = requests.post(ITEM_ENDPOINT, json=item_data, headers=headers)
        response.raise_for_status()
        duration = time.time() - start_time
        with lock:
            transaction_durations.append(duration)
        print(f"Created item for {user['email']}")
    except requests.ConnectionError as e:
        print(f"Network failure for {user['email']} - {e}")
    except requests.RequestException as e:
        with lock:
            transaction_errors += 1
            failed_transactions += 1
        print(f"Failed to create item for {user['email']} - {e}")

threads = []

# Simulate concurrent item creations with failures
for user, token in zip(users, tokens):
    thread = threading.Thread(target=create_item_with_network_failure, args=(user, token))
    threads.append(thread)
    thread.start()

# Wait for all threads to finish
for thread in threads:
    thread.join()

print("Test completed.")

# Calculate stats
total_attempts = len(users)
successful_transactions = total_attempts - failed_transactions - network_failures
error_rate = (failed_transactions / total_attempts) * 100 if total_attempts > 0 else 0
avg_duration = statistics.mean(transaction_durations) if transaction_durations else 0

print(f"Total Transactions: {total_attempts}")
print(f"Successful Transactions: {successful_transactions}")
print(f"Failed Transactions: {failed_transactions}")
# Número de errores de conexión.
print(f"Network Failures: {network_failures}")
# Número de transacciones fallidas que llegaron al servidor pero no se pudieron procesar.
print(f"Transaction Errors: {transaction_errors}")
print(f"Average Transaction Duration: {avg_duration:.2f} seconds")
print(f"Transaction Error Rate: {error_rate:.2f}%")