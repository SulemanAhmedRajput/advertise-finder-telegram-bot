# # import http.client
# # import json
# # import os
# # from dotenv import load_dotenv

# # # Load environment variables
# # load_dotenv()

# # MSG91_API_URL = "api.msg91.com"
# # MSG91_AUTH_KEY = os.getenv("MSG91_AUTH_KEY")  # Secure your auth key in .env

# # def send_otp(mobile_number, otp, template_id):
# #     """Send OTP via MSG91"""
# #     payload = {
# #         "template_id": template_id,
# #         "mobile": mobile_number,
# #         "otp": otp  # Optionally, you can let MSG91 generate the OTP by removing this field
# #     }

# #     headers = {
# #         "authkey": MSG91_AUTH_KEY,
# #         "accept": "application/json",
# #         "content-type": "application/json"
# #     }

# #     try:
# #         conn = http.client.HTTPSConnection(MSG91_API_URL)
# #         conn.request("POST", "/api/v5/otp", json.dumps(payload), headers)

# #         response = conn.getresponse()
# #         data = response.read().decode("utf-8")
# #         conn.close()

# #         print("OTP sent successfully:", data)
# #         return json.loads(data)
# #     except Exception as e:
# #         print(f"❌ Failed to send OTP: {e}")
# #         return {"error": str(e)}


# import http.client
# import json


# def send_message(auth_key, template_id, mobile, var1, var2):
#     conn = http.client.HTTPSConnection("control.msg91.com")
#     payload = json.dumps(
#         {
#             "template_id": template_id,
#             "short_url": "1",
#             "realTimeResponse": "1",
#             "recipients": [{"mobiles": mobile, "VAR1": var1, "VAR2": var2}],
#         }
#     )

#     headers = {
#         "authkey": auth_key,
#         "accept": "application/json",
#         "content-type": "application/json",
#     }

#     conn.request("POST", "/api/v5/flow", payload, headers)
#     res = conn.getresponse()
#     data = res.read().decode("utf-8")
#     print("Message Response:", data)


# def send_otp(auth_key, template_id, mobile):
#     conn = http.client.HTTPSConnection("control.msg91.com")
#     payload = json.dumps({"Param1": "value1", "Param2": "value2", "Param3": "value3"})

#     headers = {"Content-Type": "application/json", "authkey": auth_key}

#     conn.request(
#         "POST",
#         f"/api/v5/otp?otp_expiry=5&template_id={template_id}&mobile={mobile}&authkey={auth_key}",
#         payload,
#         headers,
#     )
#     res = conn.getresponse()
#     data = res.read().decode("utf-8")
#     print("OTP Response:", data)


# def verify_otp(auth_key, otp, mobile):
#     conn = http.client.HTTPSConnection("control.msg91.com")
#     headers = {"authkey": auth_key}

#     conn.request(
#         "GET", f"/api/v5/otp/verify?otp={otp}&mobile={mobile}", headers=headers
#     )
#     res = conn.getresponse()
#     data = res.read().decode("utf-8")
#     print("OTP Verification Response:", data)


# # Example Usage
# AUTH_KEY = "443525AoMYBftKu67cfe300P1"
# TEMPLATE_ID = "67cfe406d6fc054be333ea72"
# MOBILE = "+923042019543"
# VAR1 = "Test Value 1"
# VAR2 = "Test Value 2"

# # Send Message
# # send_message(AUTH_KEY, TEMPLATE_ID, MOBILE, VAR1, VAR2)

# # Send OTP
# send_otp(AUTH_KEY, TEMPLATE_ID, MOBILE)

# # # Verify OTP
# # OTP = "123456"  # Sample OTP for verification


# 1199872d-5474-4533-8c7c-dda87c270767


# POST {BASE_URL}/v1/otp/generate
# header Bearer merchant key

# POST {base_url}/v1/otp/verify


# import requests

payload = {"otp_id": "d787a306-2c6f-4f8c-ab4d-5e63fd19aaf7", "otp": "717240"}
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZGVudGlmaWVyIjo5ODkyfQ.k6__Ml2K2h41dofs2cMtW6XBA-rKIcIZNMmtcN9i9Nk",
    "Content-Type": "application/json",
}

# response = requests.post(
#     "https://api.fazpass.com/v1/otp/verify", json=payload, headers=headers
# )

# # Debugging: Print raw response details
# print(f"HTTP Status Code: {response.status_code}")
# print(f"Raw Response Text: {response.text}")  # Print the response body

# # Safely try to parse JSON
# try:
#     response_data = response.json()  # Try to parse JSON
#     print("Response JSON:", response_data)
# except requests.exceptions.JSONDecodeError:
#     print("Error: The response is not valid JSON. Check the raw response above.")



import requests
import json

def sendOTP(YOUR_PHONE_NUMBER):
    data = {
        "phone": YOUR_PHONE_NUMBER,
        "gateway_key": "1199872d-5474-4533-8c7c-dda87c270767"
    }

    headers = {
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZGVudGlmaWVyIjo5ODkyfQ.k6__Ml2K2h41dofs2cMtW6XBA-rKIcIZNMmtcN9i9Nk",
        "Content-Type": "application/json",
}

    try:
        response = requests.post('https://api.fazpass.com/v1/otp/request', 
		data=json.dumps(data), headers=headers)
        result = response.json()

        if result['status'] == True:
            return 'OTP sent successfully!'
        else:
            return 'Error: ' + (result['message'] if 'message' in result else 'Something went wrong while requesting OTP.')
    except requests.exceptions.RequestException as e:
        return 'Error: ' + str(e)

# Example usage with phone number
YOUR_PHONE_NUMBER = '923138149805'
response = sendOTP(YOUR_PHONE_NUMBER)
print(response)