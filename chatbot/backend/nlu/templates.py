"""Fixed replies (en/hi/ta) for messages the LLM layer classifies as smalltalk, clarify or an unknown
scheme name. These never come from the model, so smalltalk and clarify cannot carry model-written facts."""

GREETING = {
    "en": (
        "Hello! I can help you find government schemes, check whether you may be eligible, and verify "
        "documents. You could ask:\n"
        "- What schemes are available for farmers?\n"
        "- Am I eligible for a scholarship?\n"
        "- What documents do I need for PM-KISAN?"
    ),
    "hi": (
        "नमस्ते! मैं सरकारी योजनाएं खोजने, पात्रता जांचने और दस्तावेज़ सत्यापित करने में आपकी मदद कर सकता हूं। "
        "आप ये पूछ सकते हैं:\n"
        "- किसानों के लिए कौन सी योजनाएं हैं?\n"
        "- क्या मैं छात्रवृत्ति के लिए पात्र हूं?\n"
        "- PM-KISAN के लिए कौन से दस्तावेज चाहिए?"
    ),
    "ta": (
        "வணக்கம்! அரசு திட்டங்களைக் கண்டறியவும், தகுதியைச் சரிபார்க்கவும், ஆவணங்களைச் சரிபார்க்கவும் "
        "நான் உதவ முடியும். இவ்வாறு கேட்கலாம்:\n"
        "- விவசாயிகளுக்கு என்ன திட்டங்கள் உள்ளன?\n"
        "- நான் உதவித்தொகைக்குத் தகுதியானவரா?\n"
        "- PM-KISAN-க்கு என்ன ஆவணங்கள் தேவை?"
    ),
}

THANKS = {
    "en": "You're welcome! Ask me anything else about government schemes.",
    "hi": "आपका स्वागत है! सरकारी योजनाओं के बारे में कुछ और पूछना हो तो बताइए।",
    "ta": "வரவேற்கிறேன்! அரசு திட்டங்கள் பற்றி வேறு ஏதேனும் கேட்கலாம்.",
}

# Used when the model asks for clarification but gives no usable question.
CLARIFY = {
    "en": "Could you tell me what kind of scheme you are looking for, for example education, farming, health or housing?",
    "hi": "आप किस तरह की योजना ढूंढ रहे हैं, जैसे शिक्षा, खेती, स्वास्थ्य या आवास?",
    "ta": "நீங்கள் எந்த வகையான திட்டத்தைத் தேடுகிறீர்கள்? உதாரணமாக கல்வி, விவசாயம், சுகாதாரம், வீட்டுவசதி?",
}

NOT_FOUND = {
    "en": "I couldn't find a scheme named \"{name}\" in my data.",
    "hi": "मुझे अपने डेटा में \"{name}\" नाम की कोई योजना नहीं मिली।",
    "ta": "என் தரவில் \"{name}\" என்ற பெயரில் திட்டம் எதுவும் இல்லை.",
}

CLOSEST = {
    "en": " The closest names I have are: {names}. You can also check myscheme.gov.in.",
    "hi": " मेरे पास सबसे मिलते-जुलते नाम हैं: {names}। आप myscheme.gov.in भी देख सकते हैं।",
    "ta": " என்னிடம் உள்ள மிகவும் ஒத்த பெயர்கள்: {names}. myscheme.gov.in தளத்தையும் பார்க்கலாம்.",
}


def pick(table: dict, language: str) -> str:
    return table.get(language, table["en"])
