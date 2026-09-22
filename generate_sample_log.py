"""
generate_sample_log.py
Creates sample_server_log.txt — a synthetic log file with normal traffic and
one injected error spike, used for the final demonstration (Section 7).
Run:  python generate_sample_log.py
"""

import random
from datetime import datetime, timedelta

random.seed(42)

SOURCES = ["OrderService", "PaymentGateway", "AuthService", "InventoryService"]
NORMAL_MSGS = [
    "Request processed successfully in {ms}ms",
    "User session started for user_id={uid}",
    "Cache hit for key=product_{uid}",
    "Health check OK",
]
ERROR_MSGS = [
    "Payment gateway timeout after {ms}ms (order_id={uid})",
    "Database connection refused: retrying (attempt={uid})",
    "Payment gateway timeout after {ms}ms (order_id={uid})",
    "NullPointerException in InventoryService.reserve()",
]

start = datetime(2026, 8, 23, 10, 0, 0)
lines = []
t = start

# 5 minutes of normal traffic
for _ in range(150):
    t += timedelta(seconds=random.uniform(0.5, 2.5))
    msg = random.choice(NORMAL_MSGS).format(ms=random.randint(20, 120), uid=random.randint(1000, 9999))
    src = random.choice(SOURCES)
    lines.append(f"{t.strftime('%Y-%m-%d %H:%M:%S')} INFO [{src}] {msg}")

# 2 minute anomaly spike: bursty errors from PaymentGateway
spike_start = t
for _ in range(80):
    t += timedelta(seconds=random.uniform(0.1, 0.6))
    msg = random.choice(ERROR_MSGS).format(ms=random.randint(4000, 9000), uid=random.randint(1000, 9999))
    lines.append(f"{t.strftime('%Y-%m-%d %H:%M:%S')} ERROR [PaymentGateway] {msg}")

# 3 more minutes of normal traffic recovering
for _ in range(100):
    t += timedelta(seconds=random.uniform(0.5, 2.5))
    msg = random.choice(NORMAL_MSGS).format(ms=random.randint(20, 120), uid=random.randint(1000, 9999))
    src = random.choice(SOURCES)
    lines.append(f"{t.strftime('%Y-%m-%d %H:%M:%S')} INFO [{src}] {msg}")

with open("sample_server_log.txt", "w") as f:
    f.write("\n".join(lines) + "\n")

print(f"Wrote {len(lines)} lines. Anomaly spike starts around {spike_start.strftime('%Y-%m-%d %H:%M:%S')}.")
