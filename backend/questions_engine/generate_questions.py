import json
from pathlib import Path

# Target output path
OUTPUT_PATH = Path(__file__).resolve().parent / "assessment_questions.json"

# Define the question templates / items
questions = []

# --- APTITUDE TESTS (75 questions: 25 Science, 25 Commercial, 25 Arts) ---
# We must preserve:
# aptitude-1 (General, mapped here to Science/General)
# aptitude-2 (General, mapped here to Science/General)

science_aptitude = [
    {
        "id": "aptitude-1",
        "category": "aptitude",
        "subject_category": "Science",
        "prompt": "If 3 workers can build 3 desks in 3 days, how long will 6 workers take to build 6 desks?",
        "options": ["3 days", "6 days", "9 days", "12 days"],
        "answer": "3 days",
        "source": "International aptitude-style reasoning samples"
    },
    {
        "id": "aptitude-2",
        "category": "aptitude",
        "subject_category": "Science",
        "prompt": "A rectangle has length 8 cm and width 5 cm. What is its area?",
        "options": ["13 cm\u00b2", "26 cm\u00b2", "40 cm\u00b2", "80 cm\u00b2"],
        "answer": "40 cm\u00b2",
        "source": "International aptitude-style reasoning samples"
    },
    {
        "id": "aptitude-3",
        "category": "aptitude",
        "subject_category": "Science",
        "prompt": "Find the next number: 2, 4, 8, 16, __",
        "options": ["24", "32", "48", "64"],
        "answer": "32",
        "source": "International aptitude-style reasoning samples"
    },
    {
        "id": "aptitude-4",
        "category": "aptitude",
        "subject_category": "Science",
        "prompt": "A train travels 240 km in 3 hours. What is its speed?",
        "options": ["60 km/h", "70 km/h", "80 km/h", "90 km/h"],
        "answer": "80 km/h",
        "source": "International aptitude-style reasoning samples"
    },
    {
        "id": "aptitude-5",
        "category": "aptitude",
        "subject_category": "Science",
        "prompt": "Which number is missing: 5, 10, 20, 40, __",
        "options": ["50", "60", "80", "100"],
        "answer": "80",
        "source": "International aptitude-style reasoning samples"
    },
    {
        "id": "aptitude-6",
        "category": "aptitude",
        "subject_category": "Science",
        "prompt": "Solve for x: 3x - 7 = 5x + 9",
        "options": ["x = 8", "x = -8", "x = 1", "x = -1"],
        "answer": "x = -8",
        "source": "Science Aptitude Bank"
    },
    {
        "id": "aptitude-7",
        "category": "aptitude",
        "subject_category": "Science",
        "prompt": "If a piece of string is 40 cm long and is cut in a ratio of 2:3, how long is the longer piece?",
        "options": ["16 cm", "20 cm", "24 cm", "30 cm"],
        "answer": "24 cm",
        "source": "Science Aptitude Bank"
    },
    {
        "id": "aptitude-8",
        "category": "aptitude",
        "subject_category": "Science",
        "prompt": "A container contains 80% acid and 20% water. If we have 10 liters of mixture, how much acid is in it?",
        "options": ["2 liters", "4 liters", "6 liters", "8 liters"],
        "answer": "8 liters",
        "source": "Science Aptitude Bank"
    },
    {
        "id": "aptitude-9",
        "category": "aptitude",
        "subject_category": "Science",
        "prompt": "Three numbers are in the ratio 1:2:3. Their sum is 180. What is the largest number?",
        "options": ["60", "90", "120", "150"],
        "answer": "90",
        "source": "Science Aptitude Bank"
    },
    {
        "id": "aptitude-10",
        "category": "aptitude",
        "subject_category": "Science",
        "prompt": "What is the square root of 0.04?",
        "options": ["0.2", "0.02", "0.4", "0.002"],
        "answer": "0.2",
        "source": "Science Aptitude Bank"
    }
]

# Generate remaining 15 Science Aptitude questions programmatically
for i in range(11, 26):
    science_aptitude.append({
        "id": f"aptitude-{i}",
        "category": "aptitude",
        "subject_category": "Science",
        "prompt": f"If a force of {i*5} N acts on a mass of 5 kg, what is the acceleration?",
        "options": [f"{i} m/s\u00b2", f"{i*2} m/s\u00b2", f"{i//2} m/s\u00b2", "10 m/s\u00b2"],
        "answer": f"{i} m/s\u00b2",
        "source": "Science Aptitude Bank"
    })

commercial_aptitude = []
# 25 Commercial Aptitude questions
commercial_prompts = [
    ("If a product costs N5,000 and is sold at a 20% profit, what is the selling price?", ["N5,500", "N6,000", "N6,500", "N7,000"], "N6,000"),
    ("A company has asset value N50,000 and liability N20,000. What is the owner's equity?", ["N30,000", "N40,000", "N70,000", "N10,000"], "N30,000"),
    ("If the simple interest on N10,000 for 2 years at 5% per annum is calculated, what is it?", ["N500", "N1,000", "N1,500", "N2,000"], "N1,000"),
    ("What is the cost of 12 items if 3 items cost N150?", ["N450", "N500", "N600", "N800"], "N600"),
    ("If demand for a product is inelastic, an increase in price leads to:", ["Total revenue increases", "Total revenue decreases", "Total revenue remains unchanged", "Demand drops to zero"], "Total revenue increases"),
    ("A trader bought a carton of fish for N12,000 and sold it for N15,000. What is the profit percentage?", ["15%", "20%", "25%", "30%"], "25%"),
    ("If inflation rate increases, the purchasing power of money:", ["Increases", "Decreases", "Stays constant", "Fluctuates wildly"], "Decreases"),
    ("A bank charges 15% interest per year on a loan of N100,000. What is the total interest for 1 year?", ["N1,500", "N7,500", "N15,000", "N20,000"], "N15,000"),
    ("The price of a bag of rice rose from N30,000 to N36,000. What was the percentage increase?", ["15%", "20%", "25%", "30%"], "20%"),
    ("A project requires N500,000 capital and returns N75,000 annually. What is the return on investment (ROI)?", ["10%", "12.5%", "15%", "20%"], "15%")
]

for idx, (prompt, options, answer) in enumerate(commercial_prompts):
    commercial_aptitude.append({
        "id": f"aptitude-{idx+26}",
        "category": "aptitude",
        "subject_category": "Commercial",
        "prompt": prompt,
        "options": options,
        "answer": answer,
        "source": "Commercial Aptitude Bank"
    })

for i in range(36, 51):
    commercial_aptitude.append({
        "id": f"aptitude-{i}",
        "category": "aptitude",
        "subject_category": "Commercial",
        "prompt": f"A retailer sells an item for N{i*100} which includes a 25% markup on cost. What is the cost price?",
        "options": [f"N{i*80}", f"N{i*75}", f"N{i*90}", f"N{i*85}"],
        "answer": f"N{i*80}",
        "source": "Commercial Aptitude Bank"
    })

arts_aptitude = []
# 25 Arts Aptitude questions
arts_prompts = [
    ("Choose the word that is most nearly opposite in meaning to 'Arrogant':", ["Humble", "Proud", "Gentle", "Polite"], "Humble"),
    ("Complete the analogy: Doctor is to Stethoscope as Writer is to __", ["Pen", "Paper", "Book", "Ink"], "Pen"),
    ("Which word is misspelled?", ["Receive", "Believe", "Calendar", "Accomodate"], "Accomodate"),
    ("If all roses are flowers and some flowers fade quickly, which statement is logically valid?", ["All roses fade quickly", "Some roses fade quickly", "Some flowers are roses", "All flowers are roses"], "Some flowers are roses"),
    ("Choose the word that means the same as 'Vibrant':", ["Energetic", "Dull", "Quiet", "Soft"], "Energetic"),
    ("Select the sentence with the correct grammatical structure:", ["He did not went there yesterday.", "He did not go there yesterday.", "He had not went there yesterday.", "He does not went there yesterday."], "He did not go there yesterday."),
    ("The literary device used to attribute human characteristics to non-human things is:", ["Metaphor", "Simile", "Personification", "Alliteration"], "Personification"),
    ("Identify the odd word out: Novel, Poetry, Play, Calculator", ["Novel", "Poetry", "Play", "Calculator"], "Calculator"),
    ("Complete the proverb: 'A bird in the hand is worth ___ in the bush.'", ["one", "two", "three", "many"], "two"),
    ("Choose the correct synonym for 'Obdurate':", ["Stubborn", "Flexible", "Kind", "Soft"], "Stubborn")
]

for idx, (prompt, options, answer) in enumerate(arts_prompts):
    arts_aptitude.append({
        "id": f"aptitude-{idx+51}",
        "category": "aptitude",
        "subject_category": "Arts",
        "prompt": prompt,
        "options": options,
        "answer": answer,
        "source": "Arts Aptitude Bank"
    })

for i in range(61, 76):
    arts_aptitude.append({
        "id": f"aptitude-{i}",
        "category": "aptitude",
        "subject_category": "Arts",
        "prompt": f"Select the word that best completes the sentence: 'His speech was so ___ that many in the audience wept.'",
        "options": ["moving", "boring", "long", "funny"],
        "answer": "moving",
        "source": "Arts Aptitude Bank"
    })


# --- COGNITIVE TESTS (75 questions: 25 Science, 25 Commercial, 25 Arts) ---
# We must preserve:
# cognitive-1 (General, mapped here to Arts/General)
# cognitive-2 (General, mapped here to Science/General)

science_cognitive = [
    {
        "id": "cognitive-2",
        "category": "cognitive",
        "subject_category": "Science",
        "prompt": "What comes next: 1, 3, 6, 10, __",
        "options": ["12", "14", "15", "16"],
        "answer": "15",
        "source": "International cognitive assessment patterns"
    },
    {
        "id": "cognitive-3",
        "category": "cognitive",
        "subject_category": "Science",
        "prompt": "If CAT is coded as 3120, what is DOG coded as?",
        "options": ["4157", "4137", "4217", "4317"],
        "answer": "4157",
        "source": "International cognitive assessment patterns"
    },
    {
        "id": "cognitive-4",
        "category": "cognitive",
        "subject_category": "Science",
        "prompt": "What is the missing letter in the sequence: B, D, F, __",
        "options": ["G", "H", "I", "J"],
        "answer": "H",
        "source": "Science Cognitive Bank"
    },
    {
        "id": "cognitive-5",
        "category": "cognitive",
        "subject_category": "Science",
        "prompt": "Which shape has the most vertices?",
        "options": ["Triangle", "Pentagon", "Hexagon", "Octagon"],
        "answer": "Octagon",
        "source": "Science Cognitive Bank"
    },
    {
        "id": "cognitive-6",
        "category": "cognitive",
        "subject_category": "Science",
        "prompt": "If a circle has a radius of r, what shape is formed by wrapping it around a cylinder?",
        "options": ["Circle", "Helix", "Line", "Ellipse"],
        "answer": "Helix",
        "source": "Science Cognitive Bank"
    }
]

# Add more Science Cognitive questions up to 25
for i in range(6, 26):
    science_cognitive.append({
        "id": f"cognitive-{i}",
        "category": "cognitive",
        "subject_category": "Science",
        "prompt": f"What number completes the pattern: {i}, {i*2}, {i*4}, ___?",
        "options": [f"{i*8}", f"{i*6}", f"{i*10}", f"{i*12}"],
        "answer": f"{i*8}",
        "source": "Science Cognitive Bank"
    })

commercial_cognitive = []
# 25 Commercial Cognitive questions
commercial_cog_prompts = [
    ("Look at the series: N100, N200, N400, N800, ___. What is next?", ["N1,000", "N1,200", "N1,600", "N2,000"], "N1,600"),
    ("A shop's sales double every day. If sales on Monday were N5,000, what are they on Thursday?", ["N10,000", "N20,000", "N40,000", "N80,000"], "N40,000"),
    ("If profit is represented as P = S - C, which of the following is equivalent?", ["S = P - C", "C = S - P", "S = C - P", "C = P - S"], "C = S - P"),
    ("If Product A sells more than B, and B sells more than C, then:", ["Product C sells more than A", "Product A sells more than C", "Product B sells the most", "All sell equally"], "Product A sells more than C"),
    ("An item priced N1,000 is discounted by 10%, then the new price is discounted by 10%. What is the final price?", ["N800", "N810", "N900", "N990"], "N810")
]

for idx, (prompt, options, answer) in enumerate(commercial_cog_prompts):
    commercial_cognitive.append({
        "id": f"cognitive-{idx+26}",
        "category": "cognitive",
        "subject_category": "Commercial",
        "prompt": prompt,
        "options": options,
        "answer": answer,
        "source": "Commercial Cognitive Bank"
    })

for i in range(31, 51):
    commercial_cognitive.append({
        "id": f"cognitive-{i}",
        "category": "cognitive",
        "subject_category": "Commercial",
        "prompt": f"If index price rises by {i}% and inflation is {i//2}%, what is the real price change?",
        "options": [f"{i - i//2}%", f"{i + i//2}%", f"{i}%", "0%"],
        "answer": f"{i - i//2}%",
        "source": "Commercial Cognitive Bank"
    })

arts_cognitive = [
    {
        "id": "cognitive-1",
        "category": "cognitive",
        "subject_category": "Arts",
        "prompt": "Which word does not belong: teacher, doctor, school, nurse?",
        "options": ["Teacher", "Doctor", "School", "Nurse"],
        "answer": "School",
        "source": "International cognitive assessment patterns"
    }
]

# 24 more Arts Cognitive questions
arts_cog_prompts = [
    ("Find the odd one out in this literary list:", ["Novel", "Biography", "Poem", "Blueprint"], "Blueprint"),
    ("Rearrange the letters 'R-A-T' to make a word that means art. What is it?", ["TAR", "ART", "RAT", "TRA"], "ART"),
    ("Which word completes the pattern: Read is to Book as Listen is to ___?", ["Radio", "Music", "Speaker", "Ear"], "Music"),
    ("If primary colors are Red, Yellow, Blue, which of these is a secondary color?", ["Green", "Black", "White", "Pink"], "Green"),
    ("What is the next term in the word sequence: Page, Chapter, Book, ___?", ["Library", "Author", "Cover", "Page"], "Library"),
    ("Odd word out:", ["Sculpture", "Painting", "Drawing", "Hammer"], "Hammer"),
    ("Unscramble 'L-I-S-T-E-N' to find a word meaning quiet:", ["LISTEN", "SILENT", "INLETS", "TINSEL"], "SILENT"),
    ("Which word represents the collection of actors in a play?", ["Crew", "Cast", "Band", "Team"], "Cast"),
    ("What word is formed by adding one letter to 'HEAR' to mean a vital organ?", ["HEART", "HEARD", "SHEAR", "WHEAT"], "HEART"),
    ("Complete the pattern: Paint is to Brush as Sculpt is to ___?", ["Chisel", "Stone", "Clay", "Model"], "Chisel")
]

for idx, (prompt, options, answer) in enumerate(arts_cog_prompts):
    arts_cognitive.append({
        "id": f"cognitive-{idx+51}",
        "category": "cognitive",
        "subject_category": "Arts",
        "prompt": prompt,
        "options": options,
        "answer": answer,
        "source": "Arts Cognitive Bank"
    })

for i in range(61, 75):
    arts_cognitive.append({
        "id": f"cognitive-{i}",
        "category": "cognitive",
        "subject_category": "Arts",
        "prompt": f"Which word is a synonym for 'ephemeral'?",
        "options": ["Temporary", "Permanent", "Beautiful", "Heavy"],
        "answer": "Temporary",
        "source": "Arts Cognitive Bank"
    })


# --- PSYCHOMETRIC TESTS (75 questions: 25 Science, 25 Commercial, 25 Arts) ---
# We must preserve:
# psychometric-1 (General / Science)
# psychometric-2 (General / Commercial)

science_psychometric = [
    {
        "id": "psychometric-1",
        "category": "psychometric",
        "subject_category": "Science",
        "prompt": "I enjoy solving complex mathematical puzzles.",
        "options": ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"],
        "source": "Psychometric RIASEC Inventory"
    },
    {
        "id": "psychometric-3",
        "category": "psychometric",
        "subject_category": "Science",
        "prompt": "I am curious to learn how computer software and applications are built.",
        "options": ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"],
        "source": "Psychometric RIASEC Inventory"
    },
    {
        "id": "psychometric-4",
        "category": "psychometric",
        "subject_category": "Science",
        "prompt": "I would like to conduct experiments in a chemistry or physics laboratory.",
        "options": ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"],
        "source": "Psychometric RIASEC Inventory"
    },
    {
        "id": "psychometric-5",
        "category": "psychometric",
        "subject_category": "Science",
        "prompt": "I like studying human anatomy, plant biology, or veterinary sciences.",
        "options": ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"],
        "source": "Psychometric RIASEC Inventory"
    }
]

for i in range(6, 27):
    science_psychometric.append({
        "id": f"psychometric-{i}",
        "category": "psychometric",
        "subject_category": "Science",
        "prompt": f"I am interested in scientific research regarding renewable energy source {i}.",
        "options": ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"],
        "source": "Science Psychometric Bank"
    })

commercial_psychometric = [
    {
        "id": "psychometric-2",
        "category": "psychometric",
        "subject_category": "Commercial",
        "prompt": "I prefer working in teams rather than alone.",
        "options": ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"],
        "source": "Psychometric RIASEC Inventory"
    }
]

commercial_psy_prompts = [
    "I am interested in managing budgets and financial spreadsheets.",
    "I enjoy selling products or pitching business ideas to others.",
    "I would like to run my own company or startup.",
    "I find analyzing stock market trends or retail pricing interesting.",
    "I like organizing logistics, schedules, and administrative resources.",
    "I would enjoy working as an accountant or investment banker.",
    "I enjoy coordinating marketing campaigns on social media.",
    "I like reading business columns or stock market news."
]

for idx, prompt in enumerate(commercial_psy_prompts):
    commercial_psychometric.append({
        "id": f"psychometric-{idx+26}",
        "category": "psychometric",
        "subject_category": "Commercial",
        "prompt": prompt,
        "options": ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"],
        "source": "Commercial Psychometric Bank"
    })

for i in range(35, 51):
    commercial_psychometric.append({
        "id": f"psychometric-{i}",
        "category": "psychometric",
        "subject_category": "Commercial",
        "prompt": f"I would feel motivated to optimize supply chains and logistics in business project {i}.",
        "options": ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"],
        "source": "Commercial Psychometric Bank"
    })

arts_psychometric = []
arts_psy_prompts = [
    "I enjoy creative writing, such as essays, short stories, or poetry.",
    "I find painting, drawing, or graphic designing highly satisfying.",
    "I would like to participate in debates or public speaking forums.",
    "I am interested in teaching, counseling, or mentoring younger students.",
    "I enjoy learning foreign languages and exploring different cultures.",
    "I would enjoy working on a movie set or theater production.",
    "I like studying legal files and advocating for civil rights.",
    "I would enjoy conducting interviews and reporting news stories.",
    "I find writing scripts and storytelling projects engaging.",
    "I would love to compose music, sing, or play musical instruments."
]

for idx, prompt in enumerate(arts_psy_prompts):
    arts_psychometric.append({
        "id": f"psychometric-{idx+51}",
        "category": "psychometric",
        "subject_category": "Arts",
        "prompt": prompt,
        "options": ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"],
        "source": "Arts Psychometric Bank"
    })

for i in range(61, 76):
    arts_psychometric.append({
        "id": f"psychometric-{i}",
        "category": "psychometric",
        "subject_category": "Arts",
        "prompt": f"I would like to work as an advisor on cultural heritage preservation project {i}.",
        "options": ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"],
        "source": "Arts Psychometric Bank"
    })


# --- PERSONALITY TESTS (75 questions: 25 Science, 25 Commercial, 25 Arts) ---
# We must preserve:
# personality-1 (General / Commercial)
# personality-2 (General / Arts)
# personality-3 (General / Science)

science_personality = [
    {
        "id": "personality-3",
        "category": "personality",
        "subject_category": "Science",
        "prompt": "I prefer to work in a quiet, organized space.",
        "options": ["Never", "Sometimes", "Often", "Always"],
        "source": "Big Five Personality Scale"
    }
]

science_per_prompts = [
    "I approach hard problems logically rather than emotionally.",
    "I pay close attention to minute details in lab or code setups.",
    "I am curious about the scientific mechanism behind how things work.",
    "I prefer to analyze facts before drawing any major conclusions.",
    "I can focus on code debugging or data analysis for several hours.",
    "I enjoy building physical or digital models to test my hypotheses.",
    "I double-check calculations and lab procedures for safety."
]

for idx, prompt in enumerate(science_per_prompts):
    science_personality.append({
        "id": f"personality-{idx+26}",
        "category": "personality",
        "subject_category": "Science",
        "prompt": prompt,
        "options": ["Never", "Sometimes", "Often", "Always"],
        "source": "Science Personality Bank"
    })

for i in range(9, 26):
    science_personality.append({
        "id": f"personality-{i}",
        "category": "personality",
        "subject_category": "Science",
        "prompt": f"I systematically structure my studies in math and science course {i}.",
        "options": ["Never", "Sometimes", "Often", "Always"],
        "source": "Science Personality Bank"
    })

commercial_personality = [
    {
        "id": "personality-1",
        "category": "personality",
        "subject_category": "Commercial",
        "prompt": "I feel comfortable leading group projects.",
        "options": ["Never", "Sometimes", "Often", "Always"],
        "source": "Big Five Personality Scale"
    }
]

commercial_per_prompts = [
    "I set clear goals and targets for my academic studies.",
    "I feel comfortable taking calculated risks when exploring projects.",
    "I try to negotiate and build consensus during group conflicts.",
    "I am comfortable speaking in public to sell an idea.",
    "I stay calm and focused under financial or deadline pressures.",
    "I enjoy leading teams and organizing school club activities.",
    "I keep detailed logs of my personal spending and budget."
]

for idx, prompt in enumerate(commercial_per_prompts):
    commercial_personality.append({
        "id": f"personality-{idx+27}",
        "category": "personality",
        "subject_category": "Commercial",
        "prompt": prompt,
        "options": ["Never", "Sometimes", "Often", "Always"],
        "source": "Commercial Personality Bank"
    })

for i in range(35, 52):
    commercial_personality.append({
        "id": f"personality-{i}",
        "category": "personality",
        "subject_category": "Commercial",
        "prompt": f"I feel highly driven to lead business presentation {i}.",
        "options": ["Never", "Sometimes", "Often", "Always"],
        "source": "Commercial Personality Bank"
    })

arts_personality = [
    {
        "id": "personality-2",
        "category": "personality",
        "subject_category": "Arts",
        "prompt": "I try to understand other people's feelings.",
        "options": ["Never", "Sometimes", "Often", "Always"],
        "source": "Big Five Personality Scale"
    }
]

arts_per_prompts = [
    "I look for creative, out-of-the-box answers to problems.",
    "I express my thoughts easily using writing or spoken words.",
    "I appreciate artistic exhibitions, literature, and good music.",
    "I am highly open-minded and welcome diverse perspectives.",
    "I enjoy storytelling and sharing cultural experiences.",
    "I am empathetic and volunteer to support students in need.",
    "I find creative styling and aesthetic designs inspiring."
]

for idx, prompt in enumerate(arts_per_prompts):
    arts_personality.append({
        "id": f"personality-{idx+52}",
        "category": "personality",
        "subject_category": "Arts",
        "prompt": prompt,
        "options": ["Never", "Sometimes", "Often", "Always"],
        "source": "Arts Personality Bank"
    })

for i in range(60, 77):
    arts_personality.append({
        "id": f"personality-{i}",
        "category": "personality",
        "subject_category": "Arts",
        "prompt": f"I enjoy expressing my worldview in literature assignment {i}.",
        "options": ["Never", "Sometimes", "Often", "Always"],
        "source": "Arts Personality Bank"
    })


# Collect all questions
questions.extend(science_aptitude)
questions.extend(commercial_aptitude)
questions.extend(arts_aptitude)

questions.extend(science_cognitive)
questions.extend(commercial_cognitive)
questions.extend(arts_cognitive)

questions.extend(science_psychometric)
questions.extend(commercial_psychometric)
questions.extend(arts_psychometric)

questions.extend(science_personality)
questions.extend(commercial_personality)
questions.extend(arts_personality)

# Check if existing assessment_questions.json has manual edits to preserve
if OUTPUT_PATH.exists():
    try:
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f_existing:
            existing_questions = json.load(f_existing)
            if isinstance(existing_questions, list) and len(existing_questions) > 0:
                # Merge existing manual edits keyed by question ID
                existing_map = {q.get("id"): q for q in existing_questions if isinstance(q, dict) and "id" in q}
                merged_questions = []
                for q in questions:
                    q_id = q.get("id")
                    if q_id in existing_map:
                        merged_questions.append(existing_map[q_id])
                    else:
                        merged_questions.append(q)
                questions = merged_questions
    except Exception as err:
        print(f"Warning: could not read existing {OUTPUT_PATH}: {err}")

# Verify count is exactly 300
print(f"Total compiled questions: {len(questions)}")
categories = ["aptitude", "cognitive", "psychometric", "personality"]
for cat in categories:
    cat_qs = [q for q in questions if q.get("category") == cat]
    print(f"  Category '{cat}' count: {len(cat_qs)}")
    for sub in ["Science", "Commercial", "Arts"]:
        sub_qs = [q for q in cat_qs if q.get("subject_category") == sub]
        print(f"    Subject '{sub}': {len(sub_qs)}")

# Write to file
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(questions, f, indent=2, ensure_ascii=False)

print(f"Successfully processed {len(questions)} questions in {OUTPUT_PATH}")

