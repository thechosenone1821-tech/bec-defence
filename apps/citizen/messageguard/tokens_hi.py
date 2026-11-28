"""Hindi token set (Devanagari, plus the Hinglish-Latin overlap note).

Regexes run against normalize.normalize() output (casefolded NFKC
Devanagari is unchanged; Latin words arrive lowercase). Hinglish in
Latin script (failure mode 3 in the spec) is only partly covered here:
the most common Latin-script verbs ("bhejo", "batao", "warna") are
matched, but full transliteration variance is not.
"""

PATTERNS = [
    # --- credential -------------------------------------------------
    ("credential", "MSG-CRED-OTP-SHARE", "hi", [
        r"(बताओ|बताएं|बता\s*दो|बोलो|भेजो|भेज\s*दो|शेयर\s*करें|साझा\s*करें)\s*(मुझे\s*)?(अपना\s*)?(otp|ओटीपी)",
        r"(otp|ओटीपी)\s*.{0,25}(बताओ|बताएं|भेजें|भेजो|भेज\s*दो|भेजकर|शेयर|बता|बोलो|कन्फर्म|दोहराएं|दोहराओ|पढ़ो)",
        r"otp\s+(bhejo|batao|bata\ do|share\ karo|btado)",
    ]),
    ("credential", "MSG-CRED-CVV-SHARE", "hi", [
        r"(बताओ|बताएं|भेजो|शेयर\s*करें|कन्फर्म\s*करें)\s*(अपना\s*)?(cvv|सीवीवी)",
        r"(cvv|सीवीवी)\s*.{0,25}(बताओ|भेजो|शेयर|बताएं|कन्फर्म)",
    ]),
    ("credential", "MSG-CRED-UPI-PIN-RECEIVE", "hi", [
        r"(दर्ज|डालें|डाल|एंटर)\s*(करें\s*)?(करो\s*)?(यूपीआई|upi)\s*पिन",
        r"(यूपीआई|upi)\s*पिन\s*.{0,10}(दर्ज|डालें|डाल|एंटर)",
        r"(यूपीआई|upi)\s*पिन\s*.{0,25}(पाने\s*के\s*लिए|प्राप्त|आएगा|आ\s*जाएगा)",
    ]),
    ("credential", "MSG-CRED-UPI-COLLECT-REQUEST", "hi", [
        r"कलेक्ट\s*रिक्वेस्ट",
        r"रिक्वेस्ट\s*(स्वीकार|अप्रूव|एप्रूव)",
    ]),
    ("credential", "MSG-CRED-BANK-DETAILS", "hi", [
        r"(भेजो|भेजें|शेयर\s*करें|बताओ|बताएं|कन्फर्म)\s*(अपनी?\s*)?(बैंक|अकाउंट|खाता)\s*(डिटेल|नंबर|की\s*जानकारी)",
        r"बैंक\s*डिटेल\s*.{0,25}(भेजो|भेजें|शेयर|बताओ|कन्फर्म)",
        r"(बैंक|अकाउंट|खाता)\s*(डिटेल|नंबर|स्टेटमेंट|विवरण)\s*.{0,25}(भेजें|भेजो|शेयर|बताओ|बताएं|कन्फर्म)",
        r"\b(bank|account)\s+(details|number|statement)\b.{0,25}\b(bhejo|bhej\ do|share\ karo|batao|bhejein)\b",
    ]),
    # --- authority --------------------------------------------------
    ("authority", "MSG-AUTH-DIGITAL-ARREST", "hi", [
        r"डिजिटल\s*अरेस्ट",
        r"डिजिटली\s*गिरफ्तार",
        r"digital\ arrest\ (ka|ki)",
    ]),
    ("authority", "MSG-AUTH-ARREST-WARRANT", "hi", [
        r"गिरफ्तारी\s*(का\s*)?वारंट",
        r"वारंट\s*(जारी|निकला|आ\s*गया).{0,20}आपके\s*नाम",
        r"आपके\s*नाम\s*पर\s*(वारंट|गिरफ्तारी)",
    ]),
    ("authority", "MSG-AUTH-CASE-AGAINST-YOU", "hi", [
        r"आपके\s*खिलाफ\s*(केस|मुकदमा|रिपोर्ट|एफआईआर)",
        r"आपके\s*नाम\s*पर\s*(एफआईआर|केस|मुकदमा)",
        r"केस\s*दर्ज\s*हुआ\s*है\s*आपके\s*नाम",
    ]),
    ("authority", "MSG-AUTH-AGENCY-THREAT", "hi", [
        r"(सीबीआई|ईडी|नारकोटिक्स|कस्टम्स|कस्टम|पुलिस|आरबीआई|ट्राय|एनफोर्समेंट\s*डायरेक्टोरेट|सीमा\s*शुल्क|क्राइम\s*ब्रांच|इनकम\s*टैक्स).{0,60}(गिरफ्तार|वारंट|छाप\w*|जब्त|ब्लॉक|बंद|निलंबित|केस\s*दर्ज|हिरासत|पकड़\w*|रोक\w*|डिस्कनेक्ट)",
        r"(cbi|ed|police|customs).{0,40}(giriftaar|arrest|warrant|raiding|case)",
    ]),
    ("authority", "MSG-AUTH-PARCEL-SEIZED", "hi", [
        r"(पार्सल|कूरियर|शिपमेंट).{0,50}(जब्त|अवैध|ड्रग्स|नशीले|कस्टम्स|कस्टम)",
        r"कस्टम्स\s*(विभाग|ऑफिस|विमानन).{0,30}(पार्सल|कूरियर)",
    ]),
    ("authority", "MSG-AUTH-TELECOM-BLOCK", "hi", [
        r"(ट्राय|trai).{0,40}(ब्लॉक|बंद|डिस्कनेक्ट|निष्क्रिय)",
        r"आपका\s*[\w\s]{0,10}?(मोबाइल|नंबर|सिम|कनेक्शन).{0,30}(ब्लॉक|बंद|डिस्कनेक्ट|काट|निष्क्रिय|निलंबित)",
        r"(नंबर|सिम|कनेक्शन)\s*(ब्लॉक|डिस्कनेक्ट|बंद|निलंबित|काट)",
        r"\b(aapka|apna|your)\b.{0,10}?\b(number|sim|connection|mobile)\b.{0,30}\b(block|band|disconnect|suspend)\b",
    ]),
    ("authority", "MSG-AUTH-RBI-ACTION", "hi", [
        r"(निलंबित|ब्लॉक|फ्रीज|बंद).{0,40}आरबीआई|आरबीआई.{0,40}(निलंबित|ब्लॉक|फ्रीज|बंद)",
    ]),
    ("authority", "MSG-AUTH-POWER-DISCONNECT", "hi", [
        r"(बिजली|करंट|बिजली\s*कनेक्शन).{0,60}(काट|कट|कटौती|डिस्कनेक्ट|डिस्कनेक्शन|बंद).{0,25}(आज|आज\s*रात|अभी|तुरंत)",
        r"(आज\s*रात|आज\s*शाम|आज).{0,25}(बिजली|करंट).{0,20}(काट|कट|कटौती|डिस्कनेक्ट|डिस्कनेक्शन|बंद)",
        r"(बिजली|करंट|बिजली\s*कनेक्शन).{0,25}(आज\s*रात|आज\s*शाम|आज|तुरंत|अभी).{0,20}(काट|कट|कटौती|डिस्कनेक्ट|डिस्कनेक्शन|बंद)",
        r"बिजली\s*कनेक्शन\s*काट\s*दिया\s*जाएगा",
        r"\b(electricity|current|bijli)\b.{0,25}\b(aaj\ raat|aaj\ sham|turan?t|abhi)\b.{0,20}\b(kat|disconnect|band|cut\ off)\b",
    ]),
    # --- money_action -----------------------------------------------
    ("money_action", "MSG-MONEY-FEE-DEMAND", "hi", [
        r"(प्रोसेसिंग|रजिस्ट्रेशन|वेरिफिकेशन|जीएसटी|सर्विस|केवाईसी|kyc|एक्टिवेशन|री-?एक्टिवेशन|क्लियरेंस|स्कैनिंग|क्लेम|रिवाइवल|कनेक्शन|मेंबरशिप|जांच|निरीक्षण|री-?बुकिंग|सालाना)\s*(चार्ज|फीस|शुल्क)",
        r"कस्टम\s*ड्यूटी\s*.{0,12}?(जमा|भेजें|भरें|चुकाएं)",
        r"(चार्ज|फीस|शुल्क)\s*जमा\s*करें",
    ]),
    ("money_action", "MSG-MONEY-FINE-PENALTY", "hi", [
        r"(जुर्माना|फाइन|दंड)",
    ]),
    ("money_action", "MSG-MONEY-BAIL", "hi", [
        r"जमानत",
    ]),
    ("money_action", "MSG-MONEY-TRANSFER-DEMAND", "hi", [
        r"(भेजें|भेजो|भेज\s*दो|ट्रांसफर|जमा\s*करें|डालें)\s*₹?\s*[\d][\d,]*",
        r"₹?\s*[\d][\d,]*\s*(रुपये?|रुपए)?\s*.{0,20}?(भेजें|भेजो|भेज\s*दो|ट्रांसफर|जमा\s*करें|डालें)",
        r"₹?\s*[\d][\d,]*\s*(रुपये?|रुपए)\s*(भेजें|भेजो|भेज\s*दो|ट्रांसफर|जमा)",
        r"(भेजें|भेजो|भेज\s*दो|ट्रांसफर|जमा\s*करें)\s*.{0,25}(एजेंट|अफसर|अधिकारी|मैनेजर|को-ऑर्डिनेटर|वकील|लिनमैन|कलेक्टर|एडमिन|नीचे\s*दिए|खाते\s*में|दिए\s*गए)",
        r"(एजेंट|अफसर|अधिकारी|मैनेजर|वकील|कलेक्टर|को-ऑर्डिनेटर|एडमिन)\s*को\s*.{0,20}(भेजें|भेजो|भेज\s*दो|ट्रांसफर|जमा\s*करें)",
        r"(₹|rs\.?\s*)?[\d][\d,]*\s*.{0,25}?\b(bhejo|bhej\ do|bhejein|pay\ karo)\b",
    ]),
    # --- prize ------------------------------------------------------
    ("prize", "MSG-PRIZE-LOTTERY", "hi", [
        r"(लॉटरी|लकी\s*ड्रॉ|जैकपॉट|केबीसी|इनाम)",
        r"(kbc|lucky\ draw|lottery)",
    ]),
    ("prize", "MSG-PRIZE-WON-AMOUNT", "hi", [
        r"(जीते\s*हैं|जीता\s*है|जीते\s*हो|जीत\s*गए|जीत\s*गया)\s*₹?\s*[\d][\d,]*\s*(लाख|करोड़)",
        r"₹?\s*[\d][\d,]*\s*(लाख|करोड़)\s*(रुपये?|रुपए)?\s*(का\s*)?(इनाम|जीते|जीता|जीत)",
        r"₹?\s*[\d][\d,]*\s*(जीता\s*है|जीते\s*हैं|जीते\s*हो|जीत\s*गया|जीत\s*गए)",
        r"[\d][\d,]*\s*(jeete\ hain|jeeta\ hai|jeete\ ho|jeet\ gaye)",
    ]),
    # --- urgency ----------------------------------------------------
    ("urgency", "MSG-URG-DEADLINE-HOURS", "hi", [
        r"\d+\s*घंटे\s*(के\s*अंदर|में)",
        r"\d+\s*मिनट\s*के\s*अंदर",
        r"24\s*घंटे",
        r"आज\s*रात",
        r"आज\s*शाम",
        r"आज\s*दोपहर",
        r"\d{1,2}\s*बजे\s*तक",
        r"कल\s*सुबह\s*\d*\s*बजे\s*तक",
        r"\b\d+\s*ghant\w*\s*(me|ke\ andar)\b",
        r"\baaj\ raat\b|\baaj\ sham\b|\bkal\ tak\b",
    ]),
    ("urgency", "MSG-URG-LAST-WARNING", "hi", [
        r"अंतिम\s*चेतावनी",
        r"आखिरी\s*चेतावनी",
    ]),
    ("urgency", "MSG-URG-IMMEDIATELY", "hi", [
        r"तुरंत",
        r"फौरन",
        r"जल्दी\s*से\s*जल्दी",
        r"अभी\s*(ही|से)?\s*(करें|भेजें|भरें|चुकाएं|संपर्क|भेजो|भेज\s*दो)",
        r"अभी\s*.{0,20}?(करें|भेजें|भरें|चुकाएं|संपर्क|भेजो|भेज\s*दो)",
        r"\bturan?t\b|\bfuran\b",
        r"\babhi\b.{0,20}?\b(bhejo|bhej\ do|karo|pay|chukao|batao|bhejein)\b",
        r"\b(bhejo|bhej\ do|karo|pay|chukao|batao|bhejein)\b.{0,10}?\babhi\b",
    ]),
    ("urgency", "MSG-URG-ELSE-CLAUSE", "hi", [
        r"वरना",
        r"नहीं\s*तो",
        r"अन्यथा",
        r"warna",
    ]),
    # --- link_grab --------------------------------------------------
    ("link_grab", "MSG-LINK-CLICK-HERE", "hi", [
        r"क्लिक\s*करें",
        r"लिंक\s*पर\s*(क्लिक|जाएं|दबाएं)",
        r"यहां\s*क्लिक",
        r"click\ karo|link\ par\ click",
    ]),
    ("link_grab", "MSG-LINK-VERIFY-NOW", "hi", [
        r"(अपडेट|सत्यापित|वेरिफाई|वेरीफाई|कन्फर्म)\s*(करें|करो)\s*(अभी|अब|तुरंत)?",
        r"(अभी|तुरंत)\s*.{0,12}?(अपडेट|सत्यापित|वेरिफाई|वेरीफाई)",
        r"kyc\s*(अपडेट|update)",
    ]),
    ("link_grab", "MSG-LINK-APK", "hi", [
        r"(ऐप|एपीके|apk)\s*डाउनलोड\s*करें",
        r"नीचे\s*दिए\s*लिंक\s*से\s*डाउनलोड",
    ]),
    # Compatibility rows for the original Citizen 20-message corpus.
    ("credential", "MSG-CRED-UPI-PIN-ENTRY", "hi", [
        r"upi\s*pin.{0,20}(सबमिट|सबमिट\s+करें|दे\s+दें|बता\s+दें|बताएं|भेजें)",
        r"(सबमिट|दे\s+दें|बताएं|भेजें).{0,20}upi\s*pin",
    ]),
    ("credential", "MSG-CRED-CVV-SHARE", "hi", [
        r"(cvv|otp).{0,20}(बताएं|बता\s+दें|शेयर\s+करें|भेजें)",
    ]),
    ("link_grab", "MSG-LINK-VERIFY-NOW", "hi", [
        r"(kyc\s*)?(सत्यापन|वेरीफाई)\s*(करें|करो|कीजिए)",
    ]),

]
