

there are two different types of reaching out:

1 - hour messaging
2 - offline/online hour phone calls

- directly lets you book google calendar meetings, tell you about a house (optional) all it has to do, and works during off hours (voice AI)
- reads noreply@immobiliare.it (also other providers) and replies to the messages.

the only type that can't be accessed by AI is the online hour phone calls.




-- SIP TRUNKING:
perhaps the most crucial part of this all:
1) get a number from a provider that enables SIP accounts as welL (flynumber per ex.)
2) create a SIP account in your provider
3) curl the setup_vapi_sip.py script, it will create the credential and phone number ids in vapi.
4) ensure, from your provider, that the phone routes directly to the SIP account, not to voicemail or the landline.
5) ensure everything written in your dotenv file is correct.
