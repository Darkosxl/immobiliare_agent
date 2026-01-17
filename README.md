

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


-- GMAIL auth: 

immobiliare emails
idealista emails

gmail forwarding rule
ve calendar auth

THE DEMO:
-somebody sends an email to my gmail account
-an LLM reads the email, and gets the phone number of the person, if there is no phone number it doesn't do anything
-it hits an endpoint with the phone number, #the name of the person might be added later
-the fastapi endpoint sends an outbound call to that phone number from our vapi number
-we talk with the ai, and book an appointment,
-the appointment is set in the calendar
-it will log the conversation so the immobiliare can see it.

THE PRODUCT:

INBOUND:
-The SIP of the telesecretary when the shop is closed is routed to our vapi number
-when the office is called the AI will answer, can book a meeting or answer stuff about the apartment
-It will log the conversation, so that the immobiliare can see it.

OUTBOUND:

-immobiliare sends an email to the realtor that somebody wrote a message,
-the email is forwarded to our ai email, it gets processed by an LLM, and the phone number is taken
-The llm uses a tool to hit an endpoint with the phone number, the name of the person #their request might be added later
-the voice AI calls that number, and then they can book a meeting #or get information about the apartment this might be scraped from idealista
-it will log the conversation so the immobiliare can see it.



-LLMs:

grok-4-1-fast: thinks way too fucking much, leaked reasoning tokens into
the actual live conversation.

GROQ-kimi-k2: was perfect, was fast, was cheap, malum kisi paid for it, but
somehow it couldnt execute tool calls.

gemini-3-flash: the gemini api is way too slow. Otherwise it was great too.

openai: too expensive didnt even bother

