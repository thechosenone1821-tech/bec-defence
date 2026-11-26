"""Reason catalogue for MessageGuard.

This is the local, self-contained copy of the Part 1 reason-code
catalogue. Per the independence note in the Part 3 spec, Parts 2 and 3
share NO code beyond this catalogue, so the codes below are the only
contract surface: keep the `MSG-*` codes stable and let Part 1 remain
the source of truth for any user-facing translations (i18n).

Each reason: stable code -> (signal family, human-readable description
in English). The citizen app translates codes, not matched text.
"""

REASON_CATALOGUE = {
    # --- credential (0.45) ---
    "MSG-CRED-OTP-SHARE": (
        "credential",
        "Message asks the recipient to share, read back or confirm an OTP.",
    ),
    "MSG-CRED-CVV-SHARE": (
        "credential",
        "Message asks the recipient to share or confirm the card CVV.",
    ),
    "MSG-CRED-UPI-PIN-RECEIVE": (
        "credential",
        "Classic 'enter UPI PIN to receive money' scam: no PIN is ever needed to receive money.",
    ),
    "MSG-CRED-UPI-PIN-ENTRY": (
        "credential",
        "Message asks the recipient to enter or dial a UPI PIN from inside the chat/SMS.",
    ),
    "MSG-CRED-UPI-COLLECT-REQUEST": (
        "credential",
        "Message pushes the recipient to accept a UPI collect request (a debit, not a credit).",
    ),
    "MSG-CRED-BANK-DETAILS": (
        "credential",
        "Message asks the recipient to send bank/account details by chat or SMS.",
    ),
    # --- authority (0.40) ---
    "MSG-AUTH-DIGITAL-ARREST": (
        "authority",
        "'Digital arrest' threat; no Indian agency can legally detain anyone over a call.",
    ),
    "MSG-AUTH-ARREST-WARRANT": (
        "authority",
        "Claims an arrest warrant has been issued against the recipient.",
    ),
    "MSG-AUTH-CASE-AGAINST-YOU": (
        "authority",
        "Claims a police / legal case has been registered against the recipient.",
    ),
    "MSG-AUTH-AGENCY-THREAT": (
        "authority",
        "Impersonates an agency (CBI / ED / police / customs / TRAI / RBI) combined with arrest, raid or blocking language.",
    ),
    "MSG-AUTH-PARCEL-SEIZED": (
        "authority",
        "Parcel/courier 'seized for drugs or illegal goods' script run by customs/narcotics impersonators.",
    ),
    "MSG-AUTH-TELECOM-BLOCK": (
        "authority",
        "TRAI / telecom disconnection threat against the recipient's number or SIM.",
    ),
    "MSG-AUTH-RBI-ACTION": (
        "authority",
        "Claims RBI will suspend, block or freeze the recipient's account.",
    ),
    "MSG-AUTH-POWER-DISCONNECT": (
        "authority",
        "Electricity-board impersonation: power will be cut tonight unless a payment is made now.",
    ),
    # --- money_action (0.30) ---
    "MSG-MONEY-FEE-DEMAND": (
        "money_action",
        "Demands a processing / registration / verification / customs / GST fee to release something.",
    ),
    "MSG-MONEY-FINE-PENALTY": (
        "money_action",
        "Demands a fine or penalty payment.",
    ),
    "MSG-MONEY-BAIL": (
        "money_action",
        "Demands money for bail or a jailed relative.",
    ),
    "MSG-MONEY-TRANSFER-DEMAND": (
        "money_action",
        "Demands an explicit money transfer of a stated amount.",
    ),
    # --- prize (0.30) ---
    "MSG-PRIZE-LOTTERY": (
        "prize",
        "Lottery / lucky draw / KBC / jackpot prize claim.",
    ),
    "MSG-PRIZE-WON-AMOUNT": (
        "prize",
        "Claims the recipient won a specific large amount.",
    ),
    # --- urgency (0.20) ---
    "MSG-URG-DEADLINE-HOURS": (
        "urgency",
        "Hard deadline: 'within N hours', 'tonight at N o'clock'.",
    ),
    "MSG-URG-LAST-WARNING": (
        "urgency",
        "'Last / final warning' framing.",
    ),
    "MSG-URG-IMMEDIATELY": (
        "urgency",
        "Pressures the recipient to act 'immediately / right now'.",
    ),
    "MSG-URG-ELSE-CLAUSE": (
        "urgency",
        "'... else / warna / nahin to' consequence clause.",
    ),
    # --- link_grab (0.25) ---
    "MSG-LINK-SHORTENER": (
        "link_grab",
        "Contains a URL shortener link that hides the destination.",
    ),
    "MSG-LINK-CLICK-HERE": (
        "link_grab",
        "'Click / tap here' call-to-action on a link.",
    ),
    "MSG-LINK-VERIFY-NOW": (
        "link_grab",
        "'Verify / update / reactivate ... now' credential-harvesting phrasing around a link.",
    ),
    "MSG-LINK-LOOKALIKE-DOMAIN": (
        "link_grab",
        "Lookalike or shady-TLD domain (e.g. sbi-kyc-update.online, *.xyz, *.icu).",
    ),
    "MSG-LINK-APK": (
        "link_grab",
        "Pushes an .apk / side-loaded app download — the remote-access trojan vector.",
    ),
}


def reason_for(code: str):
    """Return (family, description) for a reason code, or None."""
    return REASON_CATALOGUE.get(code)
