 .\venv\Scripts\Activate.ps1
 Terminal 1 (backend):

uvicorn chatbot.backend.api.main:app --reload --port 8000

Terminal 2 (frontend):

cd chatbot/frontend
npm run dev

1.Scheme Search (English)
What schemes are available for farmers?
What schemes are available for SC category?
What schemes are available for women in Tamil Nadu?
What schemes are available for students?
What schemes are available for differently abled persons?
Tell me about the AICTE grant for North Eastern Region
Tell me about the 25% Capital Investment Subsidy Scheme
What is the Annal Ambedkar Business Champions Scheme?
What housing schemes are available?
What health insurance schemes are available?
What schemes are available for unemployed youth?
What agricultural schemes are available in Assam?
What education scholarships are available?
What schemes are available for self-employment?
What dairy farming schemes are available?

2.Benefits & Documents (English)
What documents do I need for the 25% Capital Investment Subsidy Scheme?
What documents are required for the AICTE GAINER scheme?
What are the benefits of the Annal Ambedkar Business Champions Scheme?
How much subsidy is available for SC/ST entrepreneurs?
What is the benefit amount for the Beej Swalamban Yojna?
How do I apply for the Chief Minister's Krishi Rinn Yojana?
What are the application steps for the AICTE infrastructure grant?
What is the financial assistance provided under the Capital Investment Subsidy?
What documents are needed for a housing scheme?
How much loan subsidy is available for students?

3.Eligibility Check (English)
Am I eligible for a housing scheme?
Am I eligible for a farming subsidy?
Am I eligible for an education scholarship?
Do I qualify for SC/ST schemes?
Can I apply for the Capital Investment Subsidy Scheme?
Check my eligibility for government schemes
Am I eligible for any scheme? I am 28 years old, OBC category, income 1.5 lakhs, from Tamil Nadu
Am I eligible for the Annal Ambedkar scheme? I am 35, SC category, from Tamil Nadu
I am a 45 year old farmer from Assam with income of 80,000. What schemes can I apply for?
I am a woman entrepreneur from Lakshadweep. Am I eligible for any subsidy?

After asking an eligibility question, the bot will ask follow-up questions. Answer them like this:
I am 30 years old
My state is Tamil Nadu
My annual income is 1.2 lakhs
I belong to SC category
I am female


4.Document Upload

Click the 📎 paperclip icon and upload a PDF. For best results use a document containing any of these fields:

Name
Date of birth or age
Annual income
Caste/category
State/address

After upload, try:

Now check my eligibility based on my uploaded document

5.Hindi Queries (switch toggle to हिंदी first)
किसानों के लिए क्या योजनाएं हैं?
महिलाओं के लिए सरकारी योजनाएं बताइए
SC वर्ग के लिए कौन सी योजनाएं हैं?
छात्रों के लिए छात्रवृत्ति योजनाएं क्या हैं?
आवास योजनाओं के बारे में बताइए
किसान क्रेडिट कार्ड के बारे में जानकारी दें
क्या मैं किसी सरकारी योजना के लिए पात्र हूं?
स्वरोजगार के लिए कौन सी योजनाएं हैं?

6.Tamil Queries (switch toggle to தமிழ் first)

Note: Tamil queries retrieve correctly but answers come back in English (known limitation — IndicTrans2 needs MSVC build tools to support Tamil output translation).

விவசாயிகளுக்கான திட்டங்கள் என்ன?
மாணவர்களுக்கான உதவித்தொகை திட்டங்கள் என்ன?
SC பிரிவினருக்கான திட்டங்கள் என்ன?
பெண்களுக்கான அரசு திட்டங்கள் என்ன?
வீட்டு மானியம் பற்றி தெரிவிக்கவும்

7.Out-of-Scope (system should decline these gracefully)
What is the capital of France?
Who is the Prime Minister of India?
Tell me a joke
What is 2 + 2?
Write me a poem
What is the weather today?
Who won the cricket match?
Tell me about ChatGPT
What stocks should I buy?
How do I cook biryani? 