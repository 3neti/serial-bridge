import serial
import threading
import queue
import json
import base64
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from cryptography.hazmat.primitives.asymmetric import ed25519
from datetime import datetime

class EnhancedKioskSimulator:
    def __init__(self, master):

        self.log_text = None
        self.master = master
        master.title("Kiosk Business Simulator v1.8")

        self.receive_queue = queue.Queue()
        self.command_queue = queue.Queue()


        self.private_key = self.load_ed25519_key()
        self.transaction_lock = threading.Lock()

        self.device_state = {
            'active': False,
            'current_transaction': None,
            'required_amount': 0.0,
            'received_amount': 0.0,
            'cards_to_dispense': 0,
            'card_stock': 50,
            'cash_box_open': False,
            'transaction_timer': None
        }

        self.log_tags = {
            'receive': {'foreground': '#009900'},    
            'send': {'foreground': '#0000FF'},      
            'error': {'foreground': '#FF0000'},   
            'warning': {'foreground': '#FFA500'},   
            'system': {'foreground': '#808080'},
            'transaction': {'foreground': '#800080'}
        }

        self.create_interface()
        self.init_serial_connection()


        self.running = True
        self.start_threads()

    def load_ed25519_key(self):
        key_seed = base64.b64decode("OqwYNFUY2ugI8yRfqgx8Io1Q4U8U6qZ2mKgmXDPyiSU=")
        return ed25519.Ed25519PrivateKey.from_private_bytes(key_seed)

    def create_interface(self):
        main_frame = ttk.Frame(self.master)
        main_frame.pack(fill=tk.BOTH, expand=True)

        status_frame = ttk.LabelFrame(main_frame, text="Transaction Status")
        status_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.Y)

        self.status_labels = {
            'transaction_id': ttk.Label(status_frame, text="Transaction ID: -"),
            'required_amount': ttk.Label(status_frame, text="Required Amount: $0.00"),
            'received_amount': ttk.Label(status_frame, text="Received Amount: $0.00"),
            'dispense_status': ttk.Label(status_frame, text="Cards to Dispense: 0"),
            'stock_level': ttk.Label(status_frame, text="Card Stock: 50"),
            'cashbox_status': ttk.Label(status_frame, text="Cash Box: Closed"),
        }

        for lbl in self.status_labels.values():
            lbl.pack(anchor=tk.W, padx=5, pady=2)

        cash_frame = ttk.LabelFrame(main_frame, text="Cash Simulation")
        cash_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.Y)

        ttk.Button(cash_frame, text="Insert $1", command=lambda: self.simulate_cash(1.0)).pack(pady=2)
        ttk.Button(cash_frame, text="Insert $5", command=lambda: self.simulate_cash(5.0)).pack(pady=2)
        ttk.Button(cash_frame, text="Insert $10", command=lambda: self.simulate_cash(10.0)).pack(pady=2)

        log_frame = ttk.LabelFrame(main_frame, text="Transaction Log")
        log_frame.pack(side=tk.RIGHT, padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, width=60)
        for tag_name, style in self.log_tags.items():
            self.log_text.tag_configure(tag_name, **style)
        self.log_text.pack(fill=tk.BOTH, expand=True)
    def init_serial_connection(self):
        try:
            self.serial = serial.Serial(
                port="COM6",
                baudrate=115200,
                timeout=1
            )
            self.log("Serial port initialized")
        except Exception as e:
            self.log(f"Serial init error: {str(e)}")
            messagebox.showerror("Connection Error", "Failed to initialize serial port")
            self.master.quit()

    def start_threads(self):
        threading.Thread(target=self.serial_listener, daemon=True).start()
        threading.Thread(target=self.process_messages, daemon=True).start()
        self.master.after(100, self.update_interface)

    def serial_listener(self):
        while self.running:
            try:
                if self.serial and self.serial.is_open:
                    raw = self.serial.readline().decode().strip()
                    if raw:
                        self.receive_queue.put(raw)  # 将消息放入队列
            except Exception as e:
                self.log(f"Serial error: {str(e)}")

    def process_messages(self):
        while self.running:
            try:
                if not self.receive_queue.empty():
                    raw_message = self.receive_queue.get()
                    self.handle_incoming(raw_message)
            except Exception as e:
                self.log(f"Message processing error: {str(e)}")
            time.sleep(0.1)

    def handle_incoming(self, raw_message):
        self.log(f"Received raw message: {raw_message}", 'receive')
        try:
            decoded = json.loads(raw_message)
            function = decoded.get('function', '').lower()

            handler = getattr(self, f"handle_{function}", None)
            if handler:
                with self.transaction_lock:
                    response = handler(decoded)
                    self.send_response(response)
            else:
                self.log(f"Unsupported function: {decoded['function']}")
        except Exception as e:
            self.log(f"Message handling error: {str(e)}")

    def handle_retrievedeviceid(self, request):
        response_data = {
            "transactionId": request['transactionId'],
            "resultCode": "200",
            "resultMessage": "Success",
            "responseTime": datetime.now().strftime("%Y%m%d%H%M%S"),
            "data": {
                "retrieveDeviceId": "DEVICE_Simulated_001",
                "phoneNumber": "+1234567890",
                "ipAddress": "192.168.1.100",
                "deviceMac": "00:1A:2B:3C:4D:5E"
            }
        }
        return response_data

    def handle_activatecashmodule(self, request):
        params = request['params']
        self.device_state.update({
            'active': True,
            'current_transaction': params['businessProcessId'],
            'required_amount': float(params['chargeTotalAmount']),
            'received_amount': 0.0,
            'cash_box_open': True
        })

        self.start_transaction_timer(params['autoShutdownTime'])

        return {
            "transactionId": request['transactionId'],
            "responseTime": datetime.now().strftime("%Y%m%d%H%M%S"),
            "resultCode": "200",
            "data": {
                "transactionId": request['transactionId'],
                "businessProcessId": params['businessProcessId'],
                "deviceBusinessId": "CASH_001"
            }
        }

    def handle_initializedevice(self, request):
        params = request['params']
        response_data = {
            "transactionId": request['transactionId'],
            "responseTime": datetime.now().strftime("%Y%m%d%H%M%S"),
            "resultCode": "200",
            "resultMessage": "Initialization successful",
            "data": {
                "businessProcessId": params['businessProcessId'],
                "deviceInitBusinessId": f"DEVICE_{params['businessProcessId']}",
                "data": {
                    "cashBoxInfo": {
                        "businessProcessId": params['businessProcessId'],
                        "chargeTotalAmount": "0.00",
                        "receivedAmount": "0.00"
                    },
                    "cardBoxInfo": {
                        "businessProcessId":params['businessProcessId'],
                        "deviceBusinessId": f"DEVICE_{params['businessProcessId']}",
                        "quantity": self.device_state['card_stock']
                    }
                }
            }
        }
        return response_data


    def handle_dispensecard(self, request):
        if self.device_state['card_stock'] < request['params']['simQuantity']:
            return self.create_error_response(request, "Insufficient card stock")

        self.device_state['cards_to_dispense'] = request['params']['simQuantity']
        return {
            "transactionId": request['transactionId'],
            "resultCode": "200",
            "data": {
                "businessProcessId": request['params']['businessProcessId'],
                "dispensedCount": self.device_state['cards_to_dispense']
            }
        }

    def simulate_cash(self, amount):
        with self.transaction_lock:
            if self.device_state['cash_box_open']:
                self.device_state['received_amount'] += amount
                self.log(f"Cash inserted: ${amount:.2f}", "transaction")

                current_time = datetime.now().strftime("%Y%m%d%H%M%S")
                transaction_id = f"UpdateCashReceived_{self.device_state['current_transaction']}_{current_time}_{str(int(time.time()))[-8:]}"

                notification = {
                    "deviceTransactionId": transaction_id,
                    "retrieveDeviceId": "DEVICE_001",
                    "function": "UpdateCashReceived",
                    "requestTime": current_time,
                    "params": {
                        "businessProcessId": self.device_state['current_transaction'],
                        "chargeTotalAmount": str(self.device_state['required_amount']),
                        "receivedTotalAmount": str(self.device_state['received_amount']),
                        "currentReceivedAmount": str(amount),
                        "isClosed": "N"
                    }
                }

                self.log(f"Sending cash received notification: {notification}", "send")
                self.send_notification(notification)

                if self.device_state['received_amount'] >= self.device_state['required_amount']:
                    notification["params"]["isClosed"] = "Y"
                    self.send_notification(notification)
                    self.complete_transaction()
            else:
                self.log("Cash box is not open", "warning")

    def handle_deactivatecashmodule(self, request):
        params = request['params']
        business_process_id = params['businessProcessId']
        close_reason = params.get('closeReason', "1") 

        if not self.device_state['active'] or self.device_state['current_transaction'] != business_process_id:
            return {
                "transactionId": request['transactionId'],
                "responseTime": datetime.now().strftime("%Y%m%d%H%M%S"),
                "resultCode": "30001",
                "resultMessage": "No active transaction or transaction ID mismatch"
            }

        if self.device_state['transaction_timer']:
            self.device_state['transaction_timer'].cancel()
            self.device_state['transaction_timer'] = None

        self.device_state['cash_box_open'] = False
        self.device_state['active'] = False

        reason_text = {
            "1": "Normal close",
            "2": "Timeout close",
            "3": "Business cancel",
            "4": "Other reason"
        }.get(close_reason, "Unknown reason")

        self.log(f"Cash box closed: {reason_text}", "transaction")

        response = {
            "transactionId": request['transactionId'],
            "responseTime": datetime.now().strftime("%Y%m%d%H%M%S"),
            "resultCode": "200",
            "resultMessage": "Cash module deactivated successfully"
        }

        return response
    def send_notification(self, notification_data):
        try:
            notification_json = json.dumps(notification_data)
            message_b64 = base64.b64encode(notification_json.encode()).decode()
            signature = self.private_key.sign(notification_json.encode())
            signature_b64 = base64.b64encode(signature).decode()

            full_message = f"{message_b64}.{signature_b64}\n"
            encoded_message = full_message.encode()

            chunk_size = 64
            for i in range(0, len(encoded_message), chunk_size):
                chunk = encoded_message[i:i+chunk_size]
                self.serial.write(chunk)
                self.serial.flush() 
                time.sleep(0.01)

            self.log(f"Notification sent: {notification_data['function']}", "transaction")
        except Exception as e:
            self.log(f"Notification send error: {str(e)}", "error")

    def complete_transaction(self):
        self.device_state.update({
            'cash_box_open': False,
            'active': False
        })

        if self.device_state['cards_to_dispense'] > 0:
            actual_dispensed = min(
                self.device_state['cards_to_dispense'],
                self.device_state['card_stock']
            )
            self.device_state['card_stock'] -= actual_dispensed
            self.log(f"Dispensed {actual_dispensed} cards", "transaction")

        self.device_state.update({
            'current_transaction': None,
            'required_amount': 0.0,
            'received_amount': 0.0,
            'cards_to_dispense': 0
        })

    def start_transaction_timer(self, timeout):
        def timeout_handler():
            with self.transaction_lock:
                if self.device_state['active']:
                    self.log("Transaction timed out", "warning")
                    self.device_state.update({
                        'active': False,
                        'cash_box_open': False
                    })

        self.device_state['transaction_timer'] = threading.Timer(timeout, timeout_handler)
        self.device_state['transaction_timer'].start()

    def send_response(self, response_data):
        try:
            response_json = json.dumps(response_data, separators=(',', ':'))
            message_b64 = base64.b64encode(response_json.encode()).decode()
            signature = self.private_key.sign(response_json.encode())
            signature_b64 = base64.b64encode(signature).decode()

            full_message = f"{message_b64}.{signature_b64}\n"
            encoded_message = full_message.encode()

            chunk_size = 64
            for i in range(0, len(encoded_message), chunk_size):
                chunk = encoded_message[i:i+chunk_size]
                self.serial.write(chunk)
                self.serial.flush()
                time.sleep(0.01)

            messageEncoded = ''.join(format(x, '02x') for x in response_json.encode())
            signatureEncoded = ''.join(format(x, '02x') for x in signature)
            self.log(f"Sent {response_data['resultCode']} response: \n Original: {response_json.strip()} \n Encoded {full_message.strip()} \n", 'send')
            self.log(f"Encoded message: {messageEncoded} \n Encoded signature: {signatureEncoded}", 'send')
        except Exception as e:
            self.log(f"Send error: {str(e)}", 'error')

    def update_interface(self):
        state = self.device_state
        self.status_labels['transaction_id'].config(
            text=f"Transaction ID: {state['current_transaction'] or 'None'}"
        )
        self.status_labels['required_amount'].config(
            text=f"Required: ${state['required_amount']:.2f}"
        )
        self.status_labels['received_amount'].config(
            text=f"Received: ${state['received_amount']:.2f}"
        )
        self.status_labels['dispense_status'].config(
            text=f"To Dispense: {state['cards_to_dispense']}"
        )
        self.status_labels['stock_level'].config(
            text=f"Stock: {state['card_stock']}"
        )
        self.status_labels['cashbox_status'].config(
            text=f"Cash Box: {'Open' if state['cash_box_open'] else 'Closed'}"
        )
        self.master.after(200, self.update_interface)

    def log(self, message, msg_type='system'):
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {message}"

        self.log_text.insert(tk.END, full_msg + '\n', msg_type)
        self.log_text.see(tk.END)
        print(full_msg)

    def on_close(self):
        self.running = False
        if self.serial.is_open:
            self.serial.close()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = EnhancedKioskSimulator(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()