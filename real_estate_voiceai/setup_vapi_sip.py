"""
Setup Vapi BYO SIP Trunk and Phone Number
Run this once to configure your FlyNumber with Vapi
"""
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

VAPI_API_KEY = os.getenv("VAPI_API_KEY")
FLYPBX_SIP_USERNAME = os.getenv("FLYPBX_SIP_USERNAME")
FLYPBX_SIP_PASSWORD = os.getenv("FLYPBX_SIP_PASSWORD")

FLYPBX_SIP_DOMAIN = os.getenv("FLYPBX_SIP_DOMAIN") or os.getenv("FLYPBX_DOMAIN") or "flypbx.com"

BASE_URL = "https://api.vapi.ai"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {VAPI_API_KEY}"
}


def create_sip_trunk_credential():
    """Step 1: Create the BYO SIP trunk credential"""
    print("=" * 60)
    print("STEP 1: Creating BYO SIP Trunk Credential...")
    print("=" * 60)
    
    url = f"{BASE_URL}/credential"
    payload = {
        "provider": "byo-sip-trunk",
        "name": "FlyNumber ITA Trunk (FlyPBX)",
        "gateways": [{
            "ip": FLYPBX_SIP_DOMAIN,
            "inboundEnabled": False
        }],
        "outboundLeadingPlusEnabled": False,
        "outboundAuthenticationPlan": {
            "authUsername": FLYPBX_SIP_USERNAME,
            "authPassword": FLYPBX_SIP_PASSWORD
        }
    }
    
    print(f"\nRequest URL: {url}")
    print(f"Request Payload:\n{json.dumps(payload, indent=2)}")
    
    response = requests.post(url, headers=HEADERS, json=payload)
    
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Body:\n{json.dumps(response.json(), indent=2)}")
    
    return response.json()


def create_byo_phone_number(credential_id):
    """Step 2: Create the BYO phone number in Vapi"""
    print("\n" + "=" * 60)
    print("STEP 2: Creating BYO Phone Number...")
    print("=" * 60)
    
    url = f"{BASE_URL}/phone-number"
    payload = {
        "provider": "byo-phone-number",
        "name": "FLYNUMBER ITA (+39 02 8126 6847)",
        "number": "390281266847",
        "numberE164CheckEnabled": False,
        "credentialId": credential_id
    }
    
    print(f"\nRequest URL: {url}")
    print(f"Request Payload:\n{json.dumps(payload, indent=2)}")
    
    response = requests.post(url, headers=HEADERS, json=payload)
    
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Body:\n{json.dumps(response.json(), indent=2)}")
    
    return response.json()


def main():
    print("\n🚀 VAPI BYO SIP TRUNK SETUP\n")
    
    # Check required env vars
    missing_vars = []
    if not VAPI_API_KEY:
        missing_vars.append("VAPI_API_KEY")
    if not FLYPBX_SIP_USERNAME:
        missing_vars.append("FLYPBX_SIP_USERNAME")
    if not FLYPBX_SIP_PASSWORD:
        missing_vars.append("FLYPBX_SIP_PASSWORD")
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these in your .env file and try again.")
        return
    
    # Step 1: Create SIP trunk credential
    credential_result = create_sip_trunk_credential()
    
    if "id" not in credential_result:
        print("\n❌ Failed to create credential. Check the error above.")
        return
    
    credential_id = credential_result["id"]
    print(f"\n✅ Credential ID: {credential_id}")
    
    # Step 2: Create BYO phone number
    phone_result = create_byo_phone_number(credential_id)
    
    if "id" not in phone_result:
        print("\n❌ Failed to create phone number. Check the error above.")
        return
    
    phone_number_id = phone_result["id"]
    print(f"\n✅ Phone Number ID: {phone_number_id}")
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ SETUP COMPLETE!")
    print("=" * 60)
    print(f"\n📋 Save these IDs in your .env file:")
    print(f"   VAPI_CREDENTIAL_ID={credential_id}")
    print(f"   VAPI_ITA_NUMBER={phone_number_id}")
    print(f"\n📞 FlyNumber forwarding target:")
    print(f"   SIP URI: sip:terminuseye@sip.vapi.ai")
    print(f"   or: sip:390281266847@{credential_id}.sip.vapi.ai")


if __name__ == "__main__":
    main()
