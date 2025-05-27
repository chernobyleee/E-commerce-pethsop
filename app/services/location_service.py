# app/services/location_service.py
import requests
import os
from flask import current_app

class LocationService:
    # UBAH INI: Tambahkan parameter ke __init__
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url_tariff = "https://api-sandbox.collaborator.komerce.id/tariff/api/v1"
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        # Logging pesan error jika api_key tidak ada, tapi jangan dari os.environ lagi di sini
        if not self.api_key:
            current_app.logger.error("KHOMSIP_API_KEY was not passed to LocationService or is empty.")


    def search_destination(self, keyword):
        """
        Search for destination addresses based on a keyword using Khomsip API.
        Returns a list of dictionaries with 'id' and 'name' (full address hierarchy),
        and other details needed for shipment creation.
        """
        if not self.api_key:
            return {"success": False, "error": "API Key not configured."}

        if len(keyword) < 3:
            return {"success": False, "error": "Keyword must be at least 3 characters."}

        url = f"{self.base_url_tariff}/destination/search"
        params = {
            "keyword": keyword
        }

        try:
            current_app.logger.debug(f"Calling Khomsip Location Search API: URL={url}, Params={params}, Headers={self.headers}")
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
            data = response.json()

            current_app.logger.debug(f"Khomsip Location Search API Raw Response (Status Code: {response.status_code}): {data}")

            khomsip_api_code = data.get('meta', {}).get('code')
            khomsip_api_message = data.get('meta', {}).get('message', 'No message from API.')
            khomsip_data_list = data.get('data')

            if khomsip_api_code == 200 and isinstance(khomsip_data_list, list) and len(khomsip_data_list) > 0:
                mapped_results = []
                for item in khomsip_data_list:
                    full_address_parts = []
                    if item.get('subdistrict_name'): full_address_parts.append(item['subdistrict_name'])
                    if item.get('district_name'): full_address_parts.append(item['district_name'])
                    if item.get('city_name'): full_address_parts.append(item['city_name'])
                    if item.get('province_name'): full_address_parts.append(item['province_name'])
                    
                    full_address = ", ".join(filter(None, full_address_parts))
                    if item.get('zip_code'):
                        full_address += f" ({item['zip_code']})"

                    mapped_results.append({
                        "id": item.get('id'),
                        "name": full_address,
                        "province": item.get('province_name'),
                        "city": item.get('city_name'),
                        "district": item.get('district_name'),
                        "subdistrict": item.get('subdistrict_name'), 
                        "zip_code": item.get('zip_code'),
                    })
                current_app.logger.info(f"Khomsip Mapped Location Results: {len(mapped_results)} items found.")
                return {"success": True, "destinations": mapped_results}
            elif khomsip_api_code == 200 and isinstance(khomsip_data_list, list) and len(khomsip_data_list) == 0:
                 current_app.logger.info(f"Khomsip API found no results for keyword: {keyword}")
                 return {"success": False, "error": "Tidak ditemukan."}
            else:
                current_app.logger.error(f"Khomsip API response not successful or missing expected data. Code: {khomsip_api_code}, Message: {khomsip_api_message}, Full Response: {data}")
                return {"success": False, "error": f"Error from API: {khomsip_api_message}"}
        except requests.exceptions.HTTPError as e:
            current_app.logger.error(f"Khomsip Search Destination API HTTP Error: {e.response.status_code} - {e.response.text}", exc_info=True)
            return {"success": False, "error": f"API Error: {e.response.status_code} - {e.response.text}"}
        except requests.exceptions.ConnectionError as e:
            current_app.logger.error(f"Khomsip Search Destination API Connection Error: {str(e)}", exc_info=True)
            return {"success": False, "error": "Koneksi ke API gagal. Coba lagi nanti."}
        except requests.exceptions.Timeout as e:
            current_app.logger.error(f"Khomsip Search Destination API Timeout Error: {str(e)}", exc_info=True)
            return {"success": False, "error": "API timeout. Coba lagi nanti."}
        except Exception as e:
            current_app.logger.error(f"Error processing Khomsip Search Destination response or unexpected error: {str(e)}", exc_info=True)
            return {"success": False, "error": "Terjadi kesalahan tak terduga saat mencari lokasi."}