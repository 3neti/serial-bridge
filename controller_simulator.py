import serial
import time

CONTROLLER_UART = "/dev/ttys013"  # From socat
BAUD_RATE = 115200

ser = serial.Serial(CONTROLLER_UART, BAUD_RATE)
print(f"🛠️ Sending simulated controller feedback to {CONTROLLER_UART}...")

# # Simulate delay and cash insert
# time.sleep(1)
# ser.write(b"COIN_VALUE=10.00\n")
#
# time.sleep(1)
# ser.write(b"CARD_DISPENSED=1\n")

# # Simulate low SIM stock
# time.sleep(1)
# ser.write(b"LOW_STOCK=3\n")
#
# # Simulate cash box removal
# time.sleep(1)
# ser.write(b"CASH_BOX_REMOVED=1250.00\n")

# Simulate card dispensed
time.sleep(1)
ser.write(b"CARD_DISPENSED=2\n")

# Simulate refund
time.sleep(1)
ser.write(b"REFUND_TRIGGERED=100.00\n")

ser.close()
print("✅ Controller simulation complete.")