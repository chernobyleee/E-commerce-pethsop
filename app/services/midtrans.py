# app/services/midtrans.py

import uuid
import json # Untuk logging payload
from flask import current_app, url_for
from datetime import datetime
import hashlib # Untuk handle_notification
import midtransclient # Library Midtrans

# Jika Anda menggunakan Decimal, pastikan diimpor
# from decimal import Decimal

class MidtransService:
    def __init__(self, server_key, client_key, is_production=False):
        self.server_key = server_key
        self.client_key = client_key
        self.is_production = is_production
        
        if self.is_production:
            self.snap_js_url = "https://app.midtrans.com/snap/snap.js"
            # self.snap_api_base_url = "https://app.midtrans.com/snap/v1/transactions"
            # self.api_url_core = "https://api.midtrans.com"
        else:
            self.snap_js_url = "https://app.sandbox.midtrans.com/snap/snap.js"
            # self.snap_api_base_url = "https://app.sandbox.midtrans.com/snap/v1/transactions"
            # self.api_url_core = "https://api.sandbox.midtrans.com"

        self.snap_client = midtransclient.Snap(
            is_production=self.is_production,
            server_key=self.server_key
            # client_key tidak diperlukan untuk Snap server-side saat membuat transaksi
        )
        
        if not self.server_key or not self.client_key: # client_key tetap dicek untuk kelengkapan config
            current_app.logger.error("Midtrans API keys (SERVER_KEY or CLIENT_KEY) are not configured.")
        else:
            current_app.logger.info(f"MidtransService initialized. Production: {self.is_production}")

    def generate_transaction_token(self, order, customer, items, shipping_fee):
        unique_order_id_for_midtrans = f"{order.invoice_number}-{str(uuid.uuid4())[:4].lower()}"
        current_app.logger.info(f"MIDTRANS SERVICE: Attempting to generate token for original_invoice: {order.invoice_number}, sending as midtrans_order_id: {unique_order_id_for_midtrans}")

        transaction_details = {
            "order_id": unique_order_id_for_midtrans,
            "gross_amount": int(order.total) # Pastikan order.total adalah numerik
        }
        
        item_details = []
        for item_obj in items: # Mengganti nama variabel 'item' menjadi 'item_obj' untuk menghindari konflik
            product_name = item_obj.product.name if item_obj.product else f"Product {item_obj.product_id}"
            item_details.append({
                "id": str(item_obj.product_id), 
                "price": int(item_obj.price), # Pastikan item_obj.price adalah numerik
                "quantity": int(item_obj.quantity), # Pastikan item_obj.quantity adalah integer
                "name": product_name,
                "merchant_name": current_app.config.get('SHOP_NAME', "PetShop")
            })
        if shipping_fee and shipping_fee > 0: # Pastikan shipping_fee adalah numerik
            item_details.append({
                "id": "SHIPPING", "price": int(shipping_fee), "quantity": 1,
                "name": "Shipping Fee", "merchant_name": current_app.config.get('SHOP_NAME', "PetShop")
            })
        if not item_details:
            current_app.logger.error(f"MIDTRANS SERVICE: item_details is empty for order {order.id}")
            return {"error": "Payment token generation failed: No items in order."}

        customer_details = {
            "first_name": customer.name.split(' ')[0] if customer.name else "Pelanggan",
            "last_name": ' '.join(customer.name.split(' ')[1:]) if customer.name and ' ' in customer.name else "",
            "email": customer.email,
            "phone": customer.phone_number or "080000000000", # Sediakan nomor default jika kosong
        }
        if order.shipment:
            customer_details["shipping_address"] = {
                "first_name": order.shipment.name.split(' ')[0] if order.shipment.name else customer_details["first_name"],
                "last_name": ' '.join(order.shipment.name.split(' ')[1:]) if order.shipment.name and ' ' in order.shipment.name else customer_details["last_name"],
                "phone": order.shipment.phone or customer_details["phone"],
                "address": order.shipment.address, 
                "city": order.shipment.city,
                "postal_code": order.shipment.zip_code, 
                "country_code": "IDN" # Kode negara Indonesia
            }
        
        notification_url_config = current_app.config.get('MIDTRANS_NOTIFICATION_URL')
        if not notification_url_config:
            current_app.logger.error("MIDTRANS_NOTIFICATION_URL is not set in config. Falling back to url_for.")
            try:
                notification_url_config = url_for('orders.midtrans_notification', _external=True)
            except RuntimeError as e:
                current_app.logger.error(f"Cannot generate MIDTRANS_NOTIFICATION_URL outside of app context and it's not configured: {e}")
                return {"error": "Server configuration error for payment notification URL."}
        
        current_app.logger.debug(f"MIDTRANS SERVICE: Notification URL for payload callbacks: {notification_url_config}")

        payload = {
            "transaction_details": transaction_details,
            "item_details": item_details,
            "customer_details": customer_details,
            "callbacks": {
                "finish": url_for('orders.order_detail', order_id=order.id, _external=True),
                "notification": notification_url_config 
            },
            "custom_expiry": { 
                "order_time": order.created_at.strftime('%Y-%m-%d %H:%M:%S +0700'), # Gunakan waktu pembuatan order
                "unit": "minute",
                "duration": current_app.config.get('MIDTRANS_EXPIRY_DURATION_MINUTES', 1440) # Default 24 jam
            }
            # Anda bisa menambahkan "enabled_payments" jika ingin membatasi metode pembayaran
        }
        
        current_app.logger.debug(f"MIDTRANS SERVICE: Final payload for {unique_order_id_for_midtrans}: {json.dumps(payload, indent=2)}")

        try:
            current_app.logger.info(f"MIDTRANS SERVICE: Attempting self.snap_client.create_transaction for {unique_order_id_for_midtrans}")
            snap_response = self.snap_client.create_transaction(payload)
            
            current_app.logger.info(f"MIDTRANS SERVICE: RAW Snap Response for {unique_order_id_for_midtrans}: {json.dumps(snap_response, indent=2)}")

            if snap_response and snap_response.get("token"):
                current_app.logger.info(f"MIDTRANS SERVICE: Token successfully extracted for {unique_order_id_for_midtrans}.")
                return {"token": snap_response.get("token"), "redirect_url": snap_response.get("redirect_url")}
            else:
                error_messages = snap_response.get("error_messages", ["Unknown error from Midtrans (token not found in response)."])
                current_app.logger.error(f"MIDTRANS SERVICE: Midtrans API Error (token not found or other issue) for {unique_order_id_for_midtrans}. Response: {snap_response}. Error Messages: {error_messages}")
                return {"error": f"Failed to generate payment token: {', '.join(error_messages)}"}

        except midtransclient.error_midtrans.MidtransAPIError as e:
            current_app.logger.error(f"MIDTRANS SERVICE: MidtransAPIError for {unique_order_id_for_midtrans}. HTTP Status: {e.api_response.status_code if e.api_response else 'N/A'}. Message: {str(e.message)}. Raw Response: {e.api_response.json() if e.api_response else 'N/A'}", exc_info=True)
            error_msg_list = []
            if e.api_response and hasattr(e.api_response, 'json') and callable(e.api_response.json):
                try:
                    error_data = e.api_response.json()
                    if isinstance(error_data, dict) and "error_messages" in error_data:
                         error_msg_list = error_data["error_messages"]
                except json.JSONDecodeError:
                    current_app.logger.warning(f"Could not decode JSON from MidtransAPIError response for {unique_order_id_for_midtrans}")

            if not error_msg_list and e.message: # Jika tidak ada error_messages, coba ambil dari e.message
                if isinstance(e.message, list): error_msg_list = e.message
                elif isinstance(e.message, str): error_msg_list = [e.message]
            
            if not error_msg_list: error_msg_list = ["Midtrans API communication error."] # Fallback
            return {"error": f"Payment Gateway Error: {', '.join(error_msg_list)}"}
        except Exception as e:
            current_app.logger.error(f"MIDTRANS SERVICE: Generic Exception during create_transaction for {unique_order_id_for_midtrans}: {str(e)}", exc_info=True)
            return {"error": f"An unexpected error occurred with payment gateway: {str(e)}"}

    def handle_notification(self, notification_data):
        current_app.logger.debug(f"Handling Midtrans Notification (Manual): {json.dumps(notification_data, indent=2)}")
        
        try:
            order_id_from_midtrans = notification_data.get('order_id') # Ini adalah ID dengan sufiks
            transaction_status = notification_data.get('transaction_status')
            status_code = notification_data.get('status_code')
            gross_amount_str = notification_data.get('gross_amount') # String, misal "10000.00"
            signature_key_from_midtrans = notification_data.get('signature_key')
            fraud_status = notification_data.get('fraud_status')

            if not all([order_id_from_midtrans, transaction_status, status_code, gross_amount_str, signature_key_from_midtrans]):
                current_app.logger.error(f"Missing essential data in notification: {notification_data}")
                return {"error": "Missing essential notification data"}

            string_to_hash = f"{order_id_from_midtrans}{status_code}{gross_amount_str}{self.server_key}"
            calculated_signature_key = hashlib.sha512(string_to_hash.encode('utf-8')).hexdigest()

            if calculated_signature_key != signature_key_from_midtrans:
                current_app.logger.warning(f"Invalid signature key for Midtrans order_id {order_id_from_midtrans}. Possible tampered notification! Calculated: {calculated_signature_key}, Received: {signature_key_from_midtrans}")
                return {"error": "Invalid signature key"}
            
            current_app.logger.info(f"Signature key validated successfully for Midtrans order_id: {order_id_from_midtrans}")

            result = {
                "order_id": order_id_from_midtrans, 
                "transaction_status": transaction_status,
                "fraud_status": fraud_status, 
                "payment_status": "pending" 
            }
            
            if transaction_status == 'capture':
                if fraud_status == 'accept':
                    result["payment_status"] = "success"
                elif fraud_status == 'challenge':
                    result["payment_status"] = "challenge"
                else: 
                    result["payment_status"] = "failed" 
                    current_app.logger.warning(f"Transaction 'capture' for {order_id_from_midtrans} but fraud_status is '{fraud_status}'. Marked as failed.")
            elif transaction_status == 'settlement':
                result["payment_status"] = "success"
            elif transaction_status == 'pending':
                result["payment_status"] = "pending"
            elif transaction_status in ['deny', 'expire', 'cancel']:
                result["payment_status"] = "failed"
            elif transaction_status in ["refund", "partial_refund", "chargeback", "partial_chargeback"]:
                result["payment_status"] = "refunded" 
            elif transaction_status == "authorize": 
                result["payment_status"] = "pending" 
            else:
                current_app.logger.warning(f"Unhandled transaction_status '{transaction_status}' for Midtrans order_id {order_id_from_midtrans}. Defaulting payment_status to 'pending'.")
            
            current_app.logger.info(f"Notification processed for Midtrans order_id {order_id_from_midtrans}. Determined payment_status: {result['payment_status']}")
            return result

        except KeyError as e:
            current_app.logger.error(f"KeyError in Midtrans notification data: {e}. Full data: {json.dumps(notification_data, indent=2)}")
            return {"error": f"Missing expected key in notification: {str(e)}"}
        except Exception as e:
            current_app.logger.error(f"Error processing Midtrans notification manually: {str(e)}", exc_info=True)
            return {"error": f"Failed to process notification: {str(e)}"}
