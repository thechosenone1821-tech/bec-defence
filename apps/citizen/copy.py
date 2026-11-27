"""Citizen-owned sentences, rendered by the shared i18n contract.

This module owns **what citizens read**. ``packages.contracts.i18n`` owns the
language-normalisation, fallback and rendering logic. The one active
model-backed capability is VIGIL image privacy.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from packages.contracts.i18n import (
    CONTRACT_VERSION, DEFAULT_LANGUAGE, HELPLINE, LANGUAGES, CitizenRenderer,
    FallbackLog, message_reason_codes as shared_message_reason_codes,
    normalise_language, reason_family,
)
from packages.contracts.reasons import REASON_CATALOGUE

ACTIVE_MODEL = "VIGIL PrivacyNet TorchScript"
VIGIL_ENABLED = True
VIGIL_MODEL_BACKED = True

CITIZEN_COPY: Dict[str, Any] = {'advisory': {'en': 'Judgement-based weighting, not calibrated against real fraud outcomes — an '
                    'aid to your decision, not a verdict.',
              'hi': 'यह मानव-निर्धारित भारांक पर आधारित है, असली धोखाधड़ी के आँकड़ों पर '
                    'कैलिब्रेटेड नहीं है — यह आपके फैसले में एक सहायता है, कोई अंतिम निर्णय नहीं।',
              'te': 'ఇది నిర్ణయించిన బరువుల ఆధారంగా పనిచేస్తుంది, నిజమైన మోసం ఫలితాలపై కాలిబ్రేట్ '
                    'చేయబడలేదు — ఇది మీ నిర్ణయానికి సహాయం మాత్రమే, తీర్పు కాదు.'},
 'band_copy': {'CRITICAL': {'en': ['This is almost certainly a scam',
                                   'Hang up now. Call 1930 and your bank immediately.'],
                            'hi': ['यह लगभग निश्चित रूप से धोखाधड़ी है',
                                   'अभी फोन काटें। 1930 और अपने बैंक को तुरंत कॉल करें।'],
                            'te': ['ఇది దాదాపు ఖచ్చితంగా మోసం',
                                   'వెంటనే ఫోన్ పెట్టేయండి. 1930కి, మీ బ్యాంకుకు వెంటనే కాల్ '
                                   'చేయండి.']},
               'ELEVATED': {'en': ['Some warning signs are present',
                                   'Pause. Verify through an official number before doing '
                                   'anything.'],
                            'hi': ['कुछ चेतावनी संकेत मौजूद हैं',
                                   'रुकें। कुछ भी करने से पहले आधिकारिक नंबर से पुष्टि करें।'],
                            'te': ['కొన్ని హెచ్చరిక సంకేతాలు ఉన్నాయి',
                                   'ఆగండి. ఏదైనా చేసే ముందు అధికారిక నంబర్ ద్వారా '
                                   'నిర్ధారించుకోండి.']},
               'HIGH': {'en': ['This looks like a scam attempt',
                               'Do not pay, do not share OTP. Call 1930.'],
                        'hi': ['यह धोखाधड़ी का प्रयास लगता है',
                               'पैसे न दें, OTP न बताएँ। 1930 पर कॉल करें।'],
                        'te': ['ఇది మోసం ప్రయత్నంలా ఉంది',
                               'డబ్బు ఇవ్వద్దు, OTP చెప్పవద్దు. 1930కి కాల్ చేయండి.']},
               'LOW': {'en': ['No known fraud warning signs found',
                              'Still never share OTP, PIN or CVV with anyone.'],
                       'hi': ['धोखाधड़ी के ज्ञात संकेत नहीं मिले',
                              'फिर भी OTP, PIN या CVV किसी को न दें।'],
                       'te': ['తెలిసిన మోసపు సంకేతాలు లేవు',
                              'అయినా OTP, PIN లేదా CVV ఎవరికీ ఇవ్వకండి.']},
               'LOW_CONFIDENCE': {'en': ['Not enough information to judge',
                                         'Trust your instinct. If they ask for money or OTP, hang '
                                         'up and call 1930.'],
                                  'hi': ['पर्याप्त जानकारी नहीं है',
                                         'अपनी समझ पर भरोसा रखें। पैसे या OTP माँगे जाएँ तो फोन '
                                         'काटें और 1930 पर कॉल करें।'],
                                  'te': ['సరిపడా సమాచారం లేదు',
                                         'మీ బుద్ధిని నమ్మండి. డబ్బు లేదా OTP అడిగితే ఫోన్ '
                                         'పెట్టేసి 1930కి కాల్ చేయండి.']}},
 'band_reason_kinds': {'below': ['too_weak',
                                 {'en': 'The signs seen so far are weak.',
                                  'hi': 'अब तक मिले संकेत कमज़ोर हैं।',
                                  'te': 'ఇప్పటివరకు కనిపించిన సంకేతాలు బలహీనంగా ఉన్నాయి.'}],
                       'corroboration': ['needs_more',
                                         {'en': 'One weak sign alone is not enough. Tell us if '
                                                'they ask for money or OTP.',
                                          'hi': 'एक कमज़ोर संकेत ही पर्याप्त नहीं है। पैसे या OTP '
                                                'माँगे जाएँ तो बताएँ।',
                                          'te': 'ఒక బలహీన సంకేతం మాత్రమే సరిపోదు. డబ్బు లేదా OTP '
                                                'అడిగితే చెప్పండి.'}],
                       'exceeds': ['reached_top',
                                   {'en': 'Several independent signs agree. Treat this as a '
                                          'serious warning.',
                                    'hi': 'कई स्वतंत्र संकेत एक ही बात कह रहे हैं। इसे गंभीर '
                                          'चेतावनी मानें।',
                                    'te': 'అనేక స్వతంత్ర సంకేతాలు ఏకీభవిస్తున్నాయి. దీన్ని '
                                          'తీవ్రమైన హెచ్చరికగా తీసుకోండి.'}],
                       'falls in': ['scored',
                                    {'en': 'Enough separate signs were seen together to raise '
                                           'this.',
                                     'hi': 'अलग-अलग संकेत साथ मिले, इसलिए यह चेतावनी बढ़ी।',
                                     'te': 'వేర్వేరు సంకేతాలు కలిసి కనిపించాయి, అందుకే ఈ హెచ్చరిక '
                                           'పెరిగింది.'}],
                       'no signals': ['nothing_seen',
                                      {'en': 'There was nothing to judge yet.',
                                       'hi': 'अभी जाँचने के लिए कुछ नहीं था।',
                                       'te': 'ఇంకా అంచనా వేయడానికి ఏమీ లేదు.'}]},
 'disclaimer': {'en': 'This is an advisory screen, not proof. Never share OTP, PIN or CVV.',
                'hi': 'यह सलाहकार जाँच है, सबूत नहीं। OTP, PIN या CVV कभी साझा न करें।',
                'te': 'ఇది సలహా పరీక్ష మాత్రమే, రుజువు కాదు. OTP, PIN లేదా CVV ఎప్పుడూ '
                      'పంచుకోవద్దు.'},
 'families': {'authority': {'en': 'It pretends to be police, a court, the RBI or a tax officer.',
                            'hi': 'यह पुलिस, अदालत, RBI या कर अधिकारी होने का दिखावा करता है।',
                            'te': 'ఇది పోలీసు, కోర్టు, RBI లేదా పన్ను అధికారిగా నటిస్తోంది.'},
              'credential': {'en': 'It asks for your OTP, PIN, CVV or password.',
                             'hi': 'यह आपका OTP, PIN, CVV या पासवर्ड माँगता है।',
                             'te': 'ఇది మీ OTP, PIN, CVV లేదా పాస్\u200cవర్డ్ అడుగుతోంది.'},
              'link_grab': {'en': 'It pushes you to click a link or verify now.',
                            'hi': 'यह लिंक पर क्लिक करने या अभी सत्यापित करने को कहता है।',
                            'te': 'లింక్ నొక్కమని లేదా వెంటనే ధృవీకరించమని చెబుతోంది.'},
              'money_action': {'en': 'It asks you to send or transfer money.',
                               'hi': 'यह पैसे भेजने या ट्रांसफर करने को कहता है।',
                               'te': 'ఇది డబ్బు పంపమని లేదా బదిలీ చేయమని అడుగుతోంది.'},
              'prize': {'en': 'It claims you won a prize or lottery.',
                        'hi': 'यह दावा करता है कि आपने इनाम या लॉटरी जीती है।',
                        'te': 'మీరు బహుమతి లేదా లాటరీ గెలిచారని చెబుతోంది.'},
              'urgency': {'en': 'It pressures you to act immediately.',
                          'hi': 'यह तुरंत कार्रवाई करने का दबाव बनाता है।',
                          'te': 'వెంటనే చర్య తీసుకోవాలని ఒత్తిడి చేస్తోంది.'}},
 'message_reason_overrides': {'MSG-CRED-UPI-PIN-RECEIVE': {'en': 'It says to enter a UPI PIN to '
                                                                 'receive money. A PIN is never '
                                                                 'needed to receive money.',
                                                           'hi': 'यह पैसे पाने के लिए UPI PIN '
                                                                 'डालने को कहता है। पैसे पाने के '
                                                                 'लिए कभी PIN नहीं चाहिए।',
                                                           'te': 'డబ్బు పొందడానికి UPI PIN నమోదు '
                                                                 'చేయమంటోంది. డబ్బు పొందడానికి PIN '
                                                                 'ఎప్పుడూ అవసరం లేదు.'},
                              'MSG-LINK-APK': {'en': 'It asks you to install an app or APK from a '
                                                     'link.',
                                               'hi': 'यह लिंक से ऐप या APK इंस्टॉल करने को कहता '
                                                     'है।',
                                               'te': 'ఇది లింక్ నుంచి యాప్ లేదా APK '
                                                     'ఇన్\u200dస్టాల్ చేయమంటోంది.'},
                              'MSG-LINK-SHORTENER': {'en': 'It hides the destination behind a '
                                                           'shortened link.',
                                                     'hi': 'यह छोटे लिंक के पीछे असली पता छुपाता '
                                                           'है।',
                                                     'te': 'ఇది చిన్న లింక్ వెనుక అసలు చిరునామా '
                                                           'దాచిపెడుతుంది.'}},
 'message_verdict': {'CRITICAL': {'en': {'action': 'Delete it. Do not pay. Call 1930 and your '
                                                   'bank.',
                                         'title': 'This is almost certainly a scam'},
                                  'hi': {'action': 'इसे हटा दें। पैसे न दें। 1930 और अपने बैंक को '
                                                   'कॉल करें।',
                                         'title': 'यह लगभग निश्चित रूप से धोखाधड़ी है'},
                                  'te': {'action': 'దీన్ని తొలగించండి. డబ్బు ఇవ్వద్దు. 1930కి, మీ '
                                                   'బ్యాంకుకు కాల్ చేయండి.',
                                         'title': 'ఇది దాదాపు ఖచ్చితంగా మోసం'}},
                     'HIGH': {'en': {'action': 'Do not reply, do not click, do not pay. Call 1930.',
                                     'title': 'This looks like a scam message'},
                              'hi': {'action': 'जवाब न दें, लिंक न खोलें, पैसे न दें। 1930 पर कॉल '
                                               'करें।',
                                     'title': 'यह धोखाधड़ी का संदेश लगता है'},
                              'te': {'action': 'రిప్లై ఇవ్వవద్దు, లింక్ నొక్కవద్దు, డబ్బు '
                                               'ఇవ్వద్దు. 1930కి కాల్ చేయండి.',
                                     'title': 'ఇది మోసపు సందేశంలా ఉంది'}},
                     'LOW': {'en': {'action': 'Still never share OTP, PIN or CVV with anyone.',
                                    'title': 'No known scam signals found'},
                             'hi': {'action': 'फिर भी OTP, PIN या CVV किसी को न दें।',
                                    'title': 'धोखाधड़ी के ज्ञात संकेत नहीं मिले'},
                             'te': {'action': 'అయినా OTP, PIN లేదా CVV ఎవరికీ ఇవ్వకండి.',
                                    'title': 'తెలిసిన మోసపు సంకేతాలు లేవు'}},
                     'MODERATE': {'en': {'action': 'Verify through the official number on your '
                                                   'card. Do not reply.',
                                         'title': 'Some warning signs are present'},
                                  'hi': {'action': 'अपने कार्ड पर दिए आधिकारिक नंबर से पुष्टि '
                                                   'करें। जवाब न दें।',
                                         'title': 'कुछ चेतावनी संकेत मौजूद हैं'},
                                  'te': {'action': 'మీ కార్డ్\u200cపై ఉన్న అధికారిక నంబర్ ద్వారా '
                                                   'నిర్ధారించుకోండి. రిప్లై ఇవ్వవద్దు.',
                                         'title': 'కొన్ని హెచ్చరిక సంకేతాలు ఉన్నాయి'}}},
 'no_message_signal': {'en': 'We recognise no known scam wording here — that is not proof it is '
                             'safe.',
                       'hi': 'यहाँ कोई ज्ञात धोखाधड़ी शब्द नहीं मिला — यह सुरक्षित होने का सबूत '
                             'नहीं है।',
                       'te': 'ఇక్కడ తెలిసిన మోసపు పదాలు లేవు — ఇది సురక్షితమని రుజువు కాదు.'},
 'privacy_tab': {'en': {'detail': 'VIGIL redacts selected image regions and reports local '
                                  'pixel-change metrics. It does not claim deepfake prevention, '
                                  'modern facial recognition defeat or anonymity. Call 1930 if in '
                                  'doubt.',
                        'title': 'Image privacy — VIGIL'},
                 'hi': {'detail': 'VIGIL चुने हुए छवि क्षेत्रों को बदलता है और स्थानीय '
                                  'पिक्सेल-परिवर्तन माप देता है। यह डीपफेक रोकथाम, आधुनिक '
                                  'चेहरा-पहचान पराजय या गुमनामी का दावा नहीं करता। संदेह हो तो '
                                  '1930 पर कॉल करें।',
                        'title': 'छवि गोपनीयता — VIGIL'},
                 'te': {'detail': 'VIGIL ఎంచుకున్న చిత్ర ప్రాంతాలను మారుస్తుంది మరియు స్థానిక '
                                  'పిక్సెల్ మార్పు కొలతలు ఇస్తుంది. ఇది డీప్\u200cఫేక్ నివారణ, '
                                  'ఆధునిక ముఖ గుర్తింపు ఓటమి లేదా అజ్ఞాతత్వానికి హామీ ఇవ్వదు. '
                                  'సందేహమైతే 1930కి కాల్ చేయండి.',
                        'title': 'చిత్ర గోప్యత — VIGIL'}},
 'reasons': {'R_LOW_CONFIDENCE': {'en': 'Not enough information to judge.',
                                  'hi': 'पर्याप्त जानकारी नहीं है।',
                                  'te': 'సరిపడా సమాచారం లేదు.'}},
 'report_copy': {'failed': {'en': ['Report not sent',
                                   'Call 1930 instead. Your data did not leave this phone.'],
                            'hi': ['रिपोर्ट नहीं भेजी गई',
                                   'इसके बजाय 1930 पर कॉल करें। आपका डेटा फ़ोन से बाहर नहीं गया।'],
                            'te': ['నివేదిక పంపబడలేదు',
                                   'బదులుగా 1930కి కాల్ చేయండి. మీ డేటా ఫోన్ నుండి బయటకు పోలేదు.']},
                 'forwarding_failed': {'en': ['Received, but not passed on',
                                              'The service took your report but could not send it '
                                              'upstream. It is on the server. Call 1930 so a '
                                              'person hears it now.'],
                                       'hi': ['रिपोर्ट मिली, लेकिन आगे नहीं भेजी जा सकी',
                                              'सेवा ने रिपोर्ट ली, पर आगे नहीं भेज सकी। यह सर्वर '
                                              'पर है। अभी 1930 पर कॉल करें ताकि किसी व्यक्ति तक '
                                              'बात पहुँचे।'],
                                       'te': ['నివేదిక అందింది, కానీ ముందుకు పంపబడలేదు',
                                              'సేవ మీ నివేదికను తీసుకుంది, కానీ ముందుకు '
                                              'పంపలేకపోయింది. అది సర్వర్\u200cపై ఉంది. ఇప్పుడే '
                                              '1930కి కాల్ చేయండి.']},
                 'offline': {'en': ['Saved on this phone',
                                    'It will be sent when you are back online. Nothing has left '
                                    'the device yet.'],
                             'hi': ['इस फ़ोन पर सहेजा गया',
                                    'ऑनलाइन होने पर भेजा जाएगा। अभी कुछ भी डिवाइस से बाहर नहीं '
                                    'गया।'],
                             'te': ['ఈ ఫోన్\u200cలో సేవ్ చేయబడింది',
                                    'ఆన్\u200cలైన్\u200cలోకి వచ్చినప్పుడు పంపబడుతుంది. ఇంకా ఏమీ '
                                    'పరికరం నుండి బయటకు పోలేదు.']},
                 'sent': {'en': ['Report sent',
                                 'Only the category, a severity band and a random token were sent. '
                                 'No image data, message text or phone number left your phone.'],
                          'hi': ['रिपोर्ट भेज दी गई',
                                 'केवल श्रेणी, गंभीरता और एक यादृच्छिक टोकन भेजा गया। आपका ऑडियो, '
                                 'संदेश या फ़ोन नंबर नहीं भेजा गया।'],
                          'te': ['నివేదిక పంపబడింది',
                                 'కేవలం వర్గం, తీవ్రత స్థాయి మరియు యాదృచ్ఛిక టోకెన్ మాత్రమే '
                                 'పంపబడ్డాయి. మీ ఆడియో, సందేశం లేదా ఫోన్ నంబర్ పంపలేదు.']}},
 'source_sentences': {'campaign': {'en': 'Other people have already reported this exact pattern.',
                                   'hi': 'अन्य लोग इसी पैटर्न की शिकायत पहले ही कर चुके हैं।',
                                   'te': 'ఇతరులు ఇదే నమూనాను ఇప్పటికే నివేదించారు.'},
                      'message:CRITICAL': {'en': 'The message uses words and demands seen in '
                                                 'confirmed fraud.',
                                           'hi': 'संदेश में पुष्ट धोखाधड़ी में देखे गए शब्द और '
                                                 'माँगें हैं।',
                                           'te': 'సందేశంలో నిర్ధారిత మోసాల్లో కనిపించే పదాలు, '
                                                 'డిమాండ్లు ఉన్నాయి.'},
                      'message:HIGH': {'en': 'The message matches a known scam pattern.',
                                       'hi': 'संदेश एक ज्ञात धोखाधड़ी पैटर्न से मेल खाता है।',
                                       'te': 'సందేశం తెలిసిన మోసం నమూనాతో సరిపోతుంది.'},
                      'repeat_contact': {'en': 'They have contacted you several times in a short '
                                               'period.',
                                         'hi': 'उन्होंने थोड़े समय में आपसे कई बार संपर्क किया है।',
                                         'te': 'వారు కొద్ది సమయంలో మీతో పలుమార్లు సంప్రదించారు.'},
                      'user_doubt': {'en': 'You felt something was wrong about this contact.',
                                     'hi': 'आपको इस संपर्क में कुछ गड़बड़ लगी।',
                                     'te': 'ఈ సంపర్కంలో ఏదో తప్పు ఉందని మీరు భావించారు.'}}}

MSG_REASON_FAMILY = {code: reason_family(code) for code in REASON_CATALOGUE}
_FALLBACK_LOG = FallbackLog()
renderer = CitizenRenderer(CITIZEN_COPY, _FALLBACK_LOG)


def render_band(band: str, lang: str = DEFAULT_LANGUAGE):
    return renderer.render_band(band, lang)


def render_advisory(lang: str = DEFAULT_LANGUAGE) -> str:
    return renderer.render_advisory(lang)


def render_band_reason(why: str, lang: str = DEFAULT_LANGUAGE) -> str:
    return renderer.render_band_reason(why, lang)


def render_reason(code: str, lang: str = DEFAULT_LANGUAGE,
                  params: Optional[Dict[str, Any]] = None) -> str:
    return renderer.render_reason(code, lang, params)


def render_family(family: str, lang: str = DEFAULT_LANGUAGE) -> str:
    return renderer.render_family(family, lang)


def render_message_reason(code: str, lang: str = DEFAULT_LANGUAGE) -> str:
    return renderer.render_message_reason(code, lang)


def render_source(signal: Dict[str, Any], lang: str = DEFAULT_LANGUAGE) -> str:
    return renderer.render_source(signal, lang)


def explain_message(result: Dict[str, Any], lang: str = DEFAULT_LANGUAGE):
    return renderer.explain_message(result, lang)


def explain_report(result: Optional[Dict[str, Any]], lang: str = DEFAULT_LANGUAGE,
                   state: str = "sent"):
    return renderer.explain_report(result, lang, state)


def privacy_tab_copy(lang: str = DEFAULT_LANGUAGE):
    return renderer.privacy_tab_copy(lang)


def catalogue_codes() -> List[str]:
    return renderer.catalogue_codes()


def fallbacks() -> List[Dict[str, str]]:
    return renderer.fallbacks()


def reset_fallbacks() -> None:
    renderer.reset_fallbacks()


def message_reason_codes() -> List[str]:
    return shared_message_reason_codes()


__all__ = [
    "CITIZEN_COPY", "CONTRACT_VERSION", "DEFAULT_LANGUAGE", "HELPLINE",
    "LANGUAGES", "MSG_REASON_FAMILY", "ACTIVE_MODEL", "VIGIL_ENABLED", "VIGIL_MODEL_BACKED",
    "catalogue_codes", "explain_message", "explain_report", "fallbacks",
    "message_reason_codes", "normalise_language", "reason_family",
    "render_advisory", "render_band", "render_band_reason", "render_family",
    "render_message_reason", "render_reason", "render_source",
    "reset_fallbacks", "privacy_tab_copy",
]
