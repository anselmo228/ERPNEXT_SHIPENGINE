# Copyright (c) 2024, Irvine Tech Hub Team6 and contributors
# For license information, please see license.txt


# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document
from frappe.utils.password import get_decrypted_password
import json
import requests
from frappe import _
import re



# 미국 주 약어 목록
us_state_abbreviations = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO",
    "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
    "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
    "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY"
}


# class SHIPENGINE(Document):
#     pass

class shipengine(Document):
	pass

def parse_address(address):
    # 주소를 줄바꿈으로 분리
    lines = address.split('<br>')
    # 주소의 첫 번째 줄을 address_line1로 사용
    address_line1 = lines[0].strip() if lines else ""

    # 도시, 주, 우편번호를 담을 변수 초기화
    city_locality = ""
    state_province = ""
    postal_code = ""

    # 주소가 최소한 2줄 이상 있는 경우, 두 번째 줄에서 추가 정보를 추출
    if len(lines) > 1:
        # 두 번째 줄을 콤마로 분리하여 도시와 주/우편번호를 분리
        second_line_parts = lines[1].split(',')
        if len(second_line_parts) >= 2:
            city_locality = second_line_parts[0].strip()
            # 주와 우편번호가 공백으로 분리되어 있는지 확인 후 분리
            state_postal = second_line_parts[1].strip().split(' ')
            if len(state_postal) > 1:
                state_province = state_postal[0].strip()
                postal_code = ' '.join(state_postal[1:]).strip()

    return address_line1, city_locality, state_province, postal_code

def parse_contact(contact):
    # HTML 태그를 제거하고 줄바꿈으로 분리
    parts = contact.replace('<br>', '\n').split('\n')
    # 전화번호만 추출 
    phone_raw = parts[-1].strip() if parts else ""
    # 숫자만 추출
    phone = re.sub(r'\D', '', phone_raw)
    return phone

def parse_pickup_name(contact):
    # HTML 태그를 제거하고 줄바꿈으로 분리
	parts = contact.replace('<br>', '\n').split('\n')
	# 이름만 추출
	name = parts[0].strip() if parts else ""
	return name
 
def get_state_abbreviation(state_name_or_abbr):
    if state_name_or_abbr in us_state_abbreviations.values():
        return state_name_or_abbr
    #  주 이름 - 약어변환
    return us_state_abbreviations.get(state_name_or_abbr, state_name_or_abbr)


def get_delivery_service(carrier):
		if carrier == "FedEx Ground®":
			return "fedex_ground"
		elif carrier == "UPS® Ground":
			return "ups_ground"
		elif carrier == "Default":
			return "tnt_uk_default"
		# elif carrier =="Hermes Postable":
		# 	return "ups_ground"
		else:
			return "ups_ground"
    

@frappe.whitelist()
def get_label(shipment_id):
    api_key = frappe.db.get_value('shipengine', '530e669a21', 'api_key')
    
    print(api_key)
    if not api_key:
        frappe.msgprint(_('API-Key is not set. Please configure it in shipengine settings.'), alert=True)
        return

    headers = {'API-Key': api_key, 'Content-Type': 'application/json'}
    
   
    try:
        # Shipment 문서 조회
        shipment_data = frappe.get_doc("Shipment", shipment_id)
        shipment_parcel_data = frappe.get_all("Shipment Parcel", 
                                      filters={"parent": shipment_id},
                                      fields=["length", "width", "height", "weight"])

        parcel = shipment_parcel_data[0]
        length = parcel['length']
        width = parcel['width']
        height = parcel['height']
        weight = parcel['weight']

        headers = {
            'API-Key': api_key,  
            'Content-Type': 'application/json'
        }
        delivery_service = get_delivery_service(shipment_data.carrier_service)
        pickup_name = parse_pickup_name(shipment_data.pickup_contact)
        delivery_address_line1, delivery_city_locality, delivery_state_province, delivery_postal_code = parse_address(shipment_data.delivery_address)
        pickup_address_line1, pickup_city_locality, pickup_state_province, pickup_postal_code = parse_address(shipment_data.pickup_address)
       
        delivery_state_province_abbr = get_state_abbreviation(delivery_state_province) 
        pickup_state_province_abbr = get_state_abbreviation(pickup_state_province) 
    
        delivery_phone = parse_contact(shipment_data.delivery_contact)

        # API 요청 바디 
        body = {
        "shipment": {# 받는
            "service_code": delivery_service,
            "ship_to": {
                "name": shipment_data.delivery_customer,
                "address_line1": delivery_address_line1,  
                "city_locality": delivery_city_locality,
                "state_province": delivery_state_province_abbr,
                "postal_code": delivery_postal_code,
                "country_code": "US",
                "address_residential_indicator": "yes"
            },
            "ship_from": {#보내는
                "name": pickup_name,
                "company_name": shipment_data.pickup,
                "phone": "222-333-4444",
                "address_line1": pickup_address_line1,
                "city_locality": pickup_city_locality,
                "state_province": pickup_state_province_abbr,
                "postal_code": pickup_postal_code,
                "country_code": "US",
                "address_residential_indicator": "no"
            },
            "packages": [
                {
                    "weight": {
                        "value": weight,
                        "unit": "ounce"
                    },
                    "dimensions": {
                        "height": height,
                        "width": width,
                        "length": length,
                        "unit": "inch"
                    }
                }]
            }  
        }

        print()
        print()
        print()
        
        print("BODY============================")

        #print("pickup : ",shipment_data.pickup)
        print("ship from name : ",pickup_name)
        
        print()
        print()
        print()
        print()
        print(body)


        # API 요청 실행
        response = requests.post('https://api.shipengine.com/v1/labels', headers=headers, json=body)
        if response.status_code == 200:
            
            response_content = response.json()
            print("RESPONSE FORM LABELS====")
            print(response_content)
            pdf_link = response_content.get("label_download", {}).get("pdf", None)
            png_link = response_content.get("label_download", {}).get("png", None)
            zpl_link = response_content.get("label_download", {}).get("zpl", None)
            carrier_id = response_content.get("carrier_id", None)

            cost_body = {
                "rate_options": {
                    "carrier_ids": [
                    carrier_id
                    ]
                },
                "shipment": {
                    "validate_address": "no_validation",
                    "ship_to": {
                    "name": shipment_data.delivery_customer,
                    "phone": delivery_phone,
                    "company_name": "",
                    "address_line1":delivery_address_line1,
                    "city_locality": delivery_city_locality,
                    "state_province": delivery_state_province_abbr,
                    "postal_code": delivery_postal_code,
                    "country_code": "US",
                    "address_residential_indicator": "no"
                    },
                    "ship_from": {
                    "name": shipment_data.owner,
                    "phone": "222-333-4444",
                    "company_name": shipment_data.pickup,
                    "address_line1": pickup_address_line1,
                    "city_locality": pickup_city_locality,
                    "state_province": pickup_state_province_abbr,
                    "postal_code":  pickup_postal_code,
                    "country_code": "US",
                    "address_residential_indicator": "no"
                    },
                    "packages": [
                    {
                        "package_code": "package",
                        "weight": {
                        "value": weight,
                        "unit": "ounce"
                        }
                    }
                    ]
                }
            }
            response_cost = requests.post('https://api.shipengine.com/v1/rates', headers = headers, json=cost_body)
            response_cost = response_cost.json()
            print("RESPONSE COST====")
            print(response_cost)
            shipping_amount = response_cost['rate_response']['rates'][0]['shipping_amount']['amount']
            print("SHIPMENT COST====")
            print(shipping_amount)
            
            if pdf_link:
                frappe.msgprint(f'<a href="{pdf_link}" target="_blank">Download as PDF</a>',"shipengine API Response")
                frappe.msgprint(f'<a href="{png_link}" target="_blank">Download as PNG</a>',"shipengine API Response")
                frappe.msgprint(f'<a href="{zpl_link}" target="_blank">Download as ZPL</a>',"shipengine API Response")
                frappe.msgprint(f'Shipping Amount: {shipping_amount}')

                #frappe.msgprint(f'<a href="{pdf_link}" target="_blank">Download as PDF</a>',f'<a> {shipping_amount} </a>',"shipengine API Response")
            else:
                frappe.msgprint('PDF link not found in the response', "shipengine API Response")
        else:
            frappe.msgprint(f'Error Occurred: {response.text}', "shipengine API Response")

    except Exception as e:
        frappe.msgprint(f'Error Occurred while printing Label: {str(e)}', "shipengine API Response")
        return []


import requests

@frappe.whitelist()
def get_Track():
    # API 키를 DocType에서 가져오기
    api_key = frappe.db.get_value('shipengine', '530e669a21', 'api_key')
    
    print("api key =",api_key)
    
    # API 키가 설정되어 있지 않은 경우, 에러 메시지 표시
    if not api_key:
        frappe.msgprint(_('API-Key is not set. Please configure it in shipengine settings.'), alert=True)
        return


    try:
        headers = {
            'API-Key': api_key
        }


        track_response = requests.get('https://api.shipengine.com/v1/tracking?carrier_code=stamps_com&tracking_number=9405511899223197428490', headers=headers)

        # Check if the request was successful
        if track_response.status_code == 200:
            track_data = track_response.json()  # Convert response to JSON format
            status_description = track_data.get('status_description')  
            status_url = track_data.get('tracking_url')  
            print(status_description)  # Print the status_description
            frappe.msgprint(f'Status: {status_description}')
            frappe.msgprint(f'<a href="{status_url}" target="_blank">USPS URL</a>',"Real Time Tracking")


        else:
            # Handle unsuccessful request
            frappe.msgprint(f'Error Occurred while Tracking: {track_response.status_code}', "Real Time Tracking")
    
    except Exception as e:
        frappe.msgprint(f'Error Occurred while Tracking: {str(e)}', "shipengine API Response")
        return []