# app/services/shipping_service.py
import requests
import os
from flask import current_app
import json # <--- PASTIKAN BARIS INI ADA! Ini penyebab error "json is not defined"


class ShippingService:
    def __init__(self, app_config):
        # KHOMSIP_API_KEY untuk fitur calculate shipping dan order
        self.komship_api_key = os.environ.get('KHOMSIP_API_KEY')
        self.base_url_tariff = "https://api-sandbox.collaborator.komerce.id/tariff/api/v1"
        self.base_url_order = "https://api-sandbox.collaborator.komerce.id/order/api/v1"

        # RAJA_ONGKIR_API_KEY untuk tracking
        self.rajaongkir_tracking_api_key = os.environ.get('RAJA_ONGKIR_API_KEY')
        self.base_url_tracking = "https://rajaongkir.komerce.id/api/v1" # URL tracking yang benar

        self.komship_headers = {
            "x-api-key": self.komship_api_key,
            "Content-Type": "application/json"
        }

        # Header untuk RajaOngkir tracking API.
        # Karena kita mengirim parameter sebagai query string, Content-Type: application/json
        # di header ini tidak relevan dan bisa menyebabkan masalah.
        self.rajaongkir_tracking_headers = {
            "key": self.rajaongkir_tracking_api_key,
            # "Content-Type": "application/json" # <--- KOMENTARI ATAU HAPUS BARIS INI
        }

        if not self.komship_api_key:
            current_app.logger.error("KHOMSIP_API_KEY not configured in environment variables for ShippingService.")
        if not self.rajaongkir_tracking_api_key:
            current_app.logger.error("RAJA_ONGKIR_API_KEY not configured in environment variables for ShippingService tracking.")

    def calculate_shipping_cost(self, origin_id, destination_id, weight, item_value=0, cod=False):
        # ... (fungsi ini tidak berubah)
        if not self.komship_api_key:
            current_app.logger.error("KHOMSIP API Key not configured for shipping calculation.")
            return {"success": False, "error": "API Key not configured."}

        url = f"{self.base_url_tariff}/calculate"
        params = {
            "shipper_destination_id": origin_id,
            "receiver_destination_id": destination_id,
            "weight": float(weight),
            "item_value": int(item_value),
            "cod": "yes" if cod else "no"
        }

        try:
            current_app.logger.debug(f"Calling Khomsip Calculate API: URL={url}, Params={params}, Headers={self.komship_headers}")
            response = requests.get(url, params=params, headers=self.komship_headers)
            response.raise_for_status()
            result = response.json()

            current_app.logger.debug(f"Khomsip Calculate API Raw Response (Status Code: {response.status_code}): {result}")

            khomsip_api_code = result.get('meta', {}).get('code')
            khomsip_api_message = result.get('meta', {}).get('message', 'No message from API.')
            
            all_rates = []
            khomsip_data_dict = result.get('data', {}) 
            
            if isinstance(khomsip_data_dict, dict):
                reguler_rates = khomsip_data_dict.get('calculate_reguler', [])
                if isinstance(reguler_rates, list):
                    all_rates.extend(reguler_rates)
                
            if khomsip_api_code == 200:
                jne_rates = []
                for rate in all_rates:
                    if rate.get('shipping_name', '').upper() == 'JNE':
                        jne_rates.append({
                            'service_code': rate.get('service_code'), 
                            'service_name': f"JNE {rate.get('service_name', '')}", 
                            'estimate_delivery_time': rate.get('etd'), 
                            'cost': rate.get('shipping_cost'), 
                        })
                
                current_app.logger.info(f"Khomsip JNE Rates Found: {len(jne_rates)} items.")
                
                if jne_rates:
                    return {"success": True, "rates": jne_rates}
                else:
                    current_app.logger.warning("No JNE shipping options found for the given criteria (after filtering).")
                    return {"success": False, "error": "Tidak ada opsi pengiriman JNE yang tersedia untuk rute ini."}
            else:
                current_app.logger.error(f"Khomsip Calculate Shipping API response not successful. Code: {khomsip_api_code}, Message: {khomsip_api_message}, Full Response: {result}")
                return {"success": False, "error": f"Error from API: {khomsip_api_message}"}
        except requests.exceptions.HTTPError as e:
            current_app.logger.error(f"Khomsip Calculate Shipping API HTTP Error: {e.response.status_code} - {e.response.text}", exc_info=True)
            return {"success": False, "error": f"API Error: {e.response.status_code} - {e.response.text}"}
        except requests.exceptions.ConnectionError as e:
            current_app.logger.error(f"Khomsip Calculate Shipping API Connection Error: {str(e)}", exc_info=True)
            return {"success": False, "error": "Koneksi ke API gagal. Coba lagi nanti."}
        except requests.exceptions.Timeout as e:
            current_app.logger.error(f"Khomsip Calculate Shipping API Timeout Error: {str(e)}", exc_info=True)
            return {"success": False, "error": "API timeout. Coba lagi nanti."}
        except Exception as e:
            current_app.logger.error(f"Error processing Khomsip Calculate Shipping response: {str(e)}", exc_info=True)
            return {"success": False, "error": "Terjadi kesalahan tak terduga saat menghitung ongkir."}


    def get_airway_bill_history(self, courier_code, airway_bill_number):
        tracking_api_url = f"{self.base_url_tracking}/track/waybill"

        courier_name_to_api_code = {
            "jne": "jne",
            "pos": "pos",
            "tiki": "tiki",
            "wahana": "wahana",
            "sicepat": "sicepat",
            "anteraja": "anteraja",
            "jnt": "j&t",
            "lion parcel": "lion",
            "jne reg23": "jne",
            "jne yes": "jne",
            "j&t express": "j&t",
            "JNE REG23": "jne",
            "JNE": "jne" # Tambahkan ini agar lebih aman
        }

        api_courier_code = courier_name_to_api_code.get(courier_code.lower(), courier_code.lower())

        if not airway_bill_number:
            current_app.logger.warning(f"Attempted to track with missing AWB: {airway_bill_number} for courier: {courier_code}")
            return {"success": False, "error": "Nomor resi tidak tersedia."}

        if not api_courier_code or api_courier_code == courier_code.lower():
            current_app.logger.warning(f"Could not map courier '{courier_code}' to a valid RajaOngkir API code. Using '{api_courier_code}'.")


        # Gunakan headers yang sudah didefinisikan di __init__
        # self.rajaongkir_tracking_headers tidak memiliki Content-Type: application/json
        headers = self.rajaongkir_tracking_headers 
        
        # Ini adalah parameter yang akan dikirim sebagai query string
        params = {
            "awb": airway_bill_number,
            "courier": api_courier_code
        }
        
        # Cetak headers dan params untuk debugging
        print(headers)
        print(params)

        try:
            current_app.logger.debug(f"Sending tracking request to {tracking_api_url} with params: {params} and headers: {headers}")
            # Lakukan POST request karena di Postman Anda berhasil dengan POST
            # Parameter di URL (query string) dikirimkan melalui `params`
            response = requests.post(tracking_api_url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            print(data)
            current_app.logger.debug(f"RajaOngkir tracking API response: {json.dumps(data)}") # json.dumps() akan berfungsi sekarang

            if data.get('meta', {}).get('status') == 'success' and data.get('data'):
                return {"success": True, "data": data['data']}
            else:
                error_message = data.get('meta', {}).get('message', 'Unknown error from API.')
                current_app.logger.error(f"RajaOngkir API returned non-success status for AWB {airway_bill_number}, Courier {api_courier_code}: {error_message}. Full response: {json.dumps(data)}")
                return {"success": False, "error": f"API RajaOngkir error: {error_message}"}

        except requests.exceptions.HTTPError as e:
            error_details = {}
            try:
                error_details = e.response.json() if e.response and e.response.content and 'application/json' in e.response.headers.get('Content-Type', '') else {}
            except ValueError:
                error_details = {"message": e.response.text}
            
            error_message = error_details.get("meta", {}).get("message", str(e))
            current_app.logger.error(f"RajaOngkir Tracking API HTTP Error: {e.response.status_code} - {error_message}")
            return {"success": False, "error": f"HTTP Error: {error_message}"}
        except requests.exceptions.ConnectionError as e:
            current_app.logger.error(f"RajaOngkir Tracking API Connection Error: {e}")
            return {"success": False, "error": f"Connection Error: {e}"}
        except requests.exceptions.Timeout as e:
            current_app.logger.error(f"RajaOngkir Tracking API Timeout: {e}")
            return {"success": False, "error": f"Timeout Error: {e}"}
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"RajaOngkir Tracking API Request Error: {e}")
            return {"success": False, "error": f"Request Error: {e}"}
        except ValueError as e:
            response_content = response.text if 'response' in locals() else "No response object"
            current_app.logger.error(f"RajaOngkir Tracking API JSON Decode Error: {e}. Response content: {response_content}")
            return {"success": False, "error": f"JSON Decode Error: {e}"}
        except Exception as e:
            current_app.logger.error(f"An unexpected error occurred during RajaOngkir Tracking API call: {e}")
            return {"success": False, "error": f"Unexpected Error: {e}"}