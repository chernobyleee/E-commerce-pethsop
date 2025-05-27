# app/services/rajaongkir.py
import requests
import os
from flask import current_app

class RajaOngkirService:
    """
    Service class to handle RajaOngkir API integration
    """
    def __init__(self):
        self.api_key = os.environ.get('RAJAONGKIR_API_KEY')
        self.base_url_tariff = "https://api-sandbox.collaborator.komerce.id/tariff/api/v1"
        self.base_url_order = "https://api-sandbox.collaborator.komerce.id/order/api/v1"
        self.headers = {
            "x-api-key": self.api_key
        }
    
    def search_destination(self, keyword):
        """
        Search for destination addresses based on a keyword
        
        Args:
            keyword (str): Keyword for search (min 3 characters)
            
        Returns:
            dict: API response with destination options
        """
        if len(keyword) < 3:
            return {"error": "Keyword must be at least 3 characters"}
        
        url = f"{self.base_url_tariff}/destination/search"
        params = {
            "keyword": keyword
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"RajaOngkir API Error: {str(e)}")
            return {"error": "Failed to search destination"}
    
    def calculate_shipping(self, origin_id, destination_id, weight, item_value=0, cod=False):
        """
        Calculate shipping costs from origin to destination
        
        Args:
            origin_id (int): Origin ID from search_destination
            destination_id (int): Destination ID from search_destination
            weight (float): Package weight in kg
            item_value (int, optional): Package value in Rupiah. Defaults to 0.
            cod (bool, optional): Whether shipping is COD. Defaults to False.
            
        Returns:
            dict: API response with shipping options and costs
        """
        url = f"{self.base_url_tariff}/calculate"
        params = {
            "shipper_destination_id": origin_id,
            "receiver_destination_id": destination_id,
            "weight": weight,
            "item_value": item_value,
            "cod": "yes" if cod else "no"
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            
            # Filter only JNE services as per requirement
            if 'data' in result and 'rates' in result['data']:
                jne_rates = [rate for rate in result['data']['rates'] if rate.get('courier_code', '').upper() == 'JNE']
                result['data']['rates'] = jne_rates
                
            return result
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"RajaOngkir API Error: {str(e)}")
            return {"error": "Failed to calculate shipping cost"}
    
    def get_airway_bill_history(self, shipping, airway_bill):
        """
        Get history and status of a shipping by airway bill number
        
        Args:
            shipping (str): Shipping courier code (JNE/SICEPAT/SAP/IDEXPRESS/J&T/NINJA)
            airway_bill (str): Airway bill number (resi)
            
        Returns:
            dict: API response with shipping status history
        """
        url = f"{self.base_url_order}/orders/history-airway-bill"
        params = {
            "shipping": shipping,
            "airway_bill": airway_bill
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"RajaOngkir API Error: {str(e)}")
            return {"error": f"Failed to get airway bill history for {shipping} - {airway_bill}"}