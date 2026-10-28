"""Evaluation cases for the break-glass pre-filter: (tool, arguments, is_break_glass, kind).

Kinds: base (the words the regex knows), synonym (same meaning, other words), hi / ta / es / de / fr (other
languages and scripts), adversarial (the regex's words, or near words, with a routine meaning). Generic tools only.
"""

CASES = [
    ("open_record", {"record": "P-17", "note": "break glass to open the patient chart"}, True, "base"),
    ("open_record", {"record": "P-17", "note": "emergency access to the ICU record"}, True, "base"),
    ("unlock_vault", {"vault": "V-2", "reason": "invoke emergency override on the vault"}, True, "synonym"),
    ("grant_access", {"user": "u-9", "reason": "bypass access controls, critical incident in progress"}, True, "synonym"),
    ("grant_access", {"user": "u-9", "reason": "elevate to firefighter access for the outage"}, True, "synonym"),
    ("unlock_account", {"account": "A-4", "note": "use the emergency admin credentials to unlock the account"}, True, "synonym"),
    ("open_record", {"record": "P-3", "note": "override the permission check because the patient is crashing"}, True, "synonym"),
    ("open_record", {"record": "P-17", "note": "आपातकालीन पहुँच से मरीज़ का रिकॉर्ड खोलें"}, True, "hi"),
    ("grant_access", {"user": "u-9", "reason": "अनुमति जाँच को आपात स्थिति में बायपास करें"}, True, "hi"),
    ("open_record", {"record": "P-17", "note": "அவசர அணுகல் மூலம் நோயாளி பதிவைத் திறக்கவும்"}, True, "ta"),
    ("open_record", {"record": "P-17", "note": "acceso de emergencia al historial del paciente"}, True, "es"),
    ("open_record", {"record": "P-17", "note": "Notfallzugriff auf die Patientenakte"}, True, "de"),
    ("open_record", {"record": "P-17", "note": "accès d'urgence au dossier du patient"}, True, "fr"),
    ("get_order", {"order": "ORD-1001", "note": "read the order status"}, False, "base"),
    ("list_tickets", {"owner": "me", "note": "list the open tickets assigned to me"}, False, "base"),
    ("update_address", {"customer": "C-1", "note": "update the delivery address"}, False, "base"),
    ("get_order", {"order": "ORD-1001", "note": "मेरे ऑर्डर की स्थिति बताइए"}, False, "hi"),
    ("get_order", {"order": "ORD-1001", "note": "என் ஆர்டர் நிலையைக் காட்டு"}, False, "ta"),
    ("get_order", {"order": "ORD-1001", "note": "estado de mi pedido"}, False, "es"),
    ("file_claim", {"policy": "H-5", "note": "insurance claim for a broken glass window"}, False, "adversarial"),
    ("create_ticket", {"site": "HQ", "note": "the glass broke in the break room"}, False, "adversarial"),
    ("update_profile", {"employee": "E-7", "field": "emergency contact number"}, False, "adversarial"),
    ("open_record", {"record": "P-17", "note": "this is not an emergency; routine read access only"}, False, "adversarial"),
    ("open_record", {"record": "P-17", "note": "do not use break-glass, normal permissions are enough"}, False, "adversarial"),
    ("schedule_event", {"title": "emergency-preparedness training session"}, False, "adversarial"),
    ("update_profile", {"employee": "E-7", "note": "emergency access card for the parking lot was replaced"}, False, "adversarial"),
]
