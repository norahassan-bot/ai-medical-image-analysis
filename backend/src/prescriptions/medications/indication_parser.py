"""Verified clinical drug knowledge repository providing educational summaries and general therapeutic indications."""

from typing import Dict, Any, List, Optional


# Curated, verified pharmaceutical reference knowledge repository for essential medications
VERIFIED_MEDICATION_KNOWLEDGE: Dict[str, Dict[str, Any]] = {
    "augmentin": {
        "canonical_name": "Augmentin",
        "generic_name": "Amoxicillin / Clavulanic Acid",
        "active_ingredients": ["Amoxicillin Trihydrate", "Clavulanate Potassium"],
        "drug_class": "Penicillin-class Antibacterial / Beta-lactamase Inhibitor combination",
        "what_is_it": "Augmentin is a combination antibacterial medication containing amoxicillin and clavulanate potassium that works by inhibiting bacterial cell wall synthesis and preventing enzymatic bacterial resistance.",
        "what_is_it_ar": "أوجمنتين هو مضاد حيوي مركب يحتوي على أموكسيسيلين ومثبط إنزيم بيتا-لاكتاماز (كلافولانات) يعمل على علاج العدوى البكتيرية ومنع مقاومة البكتيريا.",
        "general_uses": [
            "Bacterial respiratory tract infections (bronchitis, pneumonia)",
            "Ear, nose, and throat bacterial infections (sinusitis, otitis media)",
            "Skin and soft tissue bacterial infections",
            "Urinary tract bacterial infections"
        ],
        "general_uses_ar": [
            "التهابات الجهاز التنفسي البكتيرية (الالتهاب الرئوي، التهاب الشعب الهوائية)",
            "عدوى الأذن والأنف والحنجرة (التهاب الجيوب الأنفية، التهاب الأذن الوسطى)",
            "عدوى الجلد والأنسجة الرخوة البكتيرية",
            "عدوى المسالك البولية البكتيرية"
        ],
        "standard_route": "Oral",
        "standard_route_ar": "عن طريق الفم"
    },
    "amoxicillin": {
        "canonical_name": "Amoxicillin",
        "generic_name": "Amoxicillin",
        "active_ingredients": ["Amoxicillin"],
        "drug_class": "Aminopenicillin Antibacterial",
        "what_is_it": "Amoxicillin is a broad-spectrum penicillin-type antibiotic used to treat susceptible bacterial infections.",
        "what_is_it_ar": "أموكسيسيلين هو مضاد حيوي واسع المجال من عائلة البنسلين يستخدم لعلاج العدوى البكتيرية الحساسة له.",
        "general_uses": [
            "Upper and lower respiratory tract bacterial infections",
            "Dental and oral infections",
            "Urinary tract infections",
            "Skin and ear bacterial infections"
        ],
        "general_uses_ar": [
            "عدوى الجهاز التنفسي العلوي والسفلي البكتيرية",
            "عدوى الأسنان واللثة",
            "التهابات المسالك البولية",
            "عدوى الجلد والأذن البكتيرية"
        ],
        "standard_route": "Oral",
        "standard_route_ar": "عن طريق الفم"
    },
    "cataflam": {
        "canonical_name": "Cataflam",
        "generic_name": "Diclofenac Potassium",
        "active_ingredients": ["Diclofenac Potassium"],
        "drug_class": "Non-Steroidal Anti-Inflammatory Drug (NSAID)",
        "what_is_it": "Cataflam contains diclofenac potassium, a fast-acting non-steroidal anti-inflammatory drug that provides analgesic and anti-inflammatory action by inhibiting cyclooxygenase (COX) enzymes.",
        "what_is_it_ar": "كاتافلام يحتوي على ديكلوفيناك البوتاسيوم، وهو مسكن سريع المفعول ومضاد للالتهاب غير ستيرويدي يعمل على تخفيف الألم والالتهاب.",
        "general_uses": [
            "Short-term relief of acute pain and inflammatory episodes",
            "Dental and post-operative pain",
            "Musculoskeletal sprains, strains, and joint pain",
            "Dysmenorrhea (menstrual pain)"
        ],
        "general_uses_ar": [
            "تسكين الآلام الحادة والالتهابات قصيرة المدى",
            "آلام الأسنان وما بعد العمليات الجراحية",
            "آلام العضلات والمفاصل والالتواءات",
            "تسكين آلام الدورة الشهرية"
        ],
        "standard_route": "Oral",
        "standard_route_ar": "عن طريق الفم"
    },
    "panadol": {
        "canonical_name": "Panadol",
        "generic_name": "Paracetamol (Acetaminophen)",
        "active_ingredients": ["Paracetamol"],
        "drug_class": "Analgesic and Antipyretic",
        "what_is_it": "Panadol contains paracetamol, an established non-opioid analgesic and antipyretic agent used for mild to moderate pain relief and fever reduction.",
        "what_is_it_ar": "بانادول يحتوي على باراسيتامول، وهو مسكن للألم وخافض للحرارة يستخدم لتسكين الآلام الخفيفة إلى المتوسطة وخفض درجة حرارة الجسم.",
        "general_uses": [
            "Mild to moderate headache and migraine pain",
            "Fever reduction associated with colds and flu",
            "Muscular aches and sore throat",
            "Dental ache and teething discomfort"
        ],
        "general_uses_ar": [
            "تسكين الصداع وآلام الرأس الخفيفة إلى المتوسطة",
            "خفض درجات الحرارة المصاحبة للبرد والإنفلونزا",
            "آلام العضلات والتهاب الحلق",
            "آلام الأسنان"
        ],
        "standard_route": "Oral",
        "standard_route_ar": "عن طريق الفم"
    },
    "congestal": {
        "canonical_name": "Congestal",
        "generic_name": "Paracetamol / Pseudoephedrine / Chlorpheniramine",
        "active_ingredients": ["Paracetamol", "Pseudoephedrine Hydrochloride", "Chlorpheniramine Maleate"],
        "drug_class": "Multi-symptom Cold and Flu combination",
        "what_is_it": "Congestal is a combination medicine formulated with an analgesic (paracetamol), a decongestant (pseudoephedrine), and an antihistamine (chlorpheniramine) to relieve nasal and cold symptoms.",
        "what_is_it_ar": "كونجستال هو دواء مركب يحتوي على مسكن وخافض حرارة (باراسيتامول)، ومزيل احتقان (سودوإيفيدرين)، ومضاد للحساسية (كلورفينيرامين) لتخفيف أعراض نزلات البرد.",
        "general_uses": [
            "Relief of common cold and influenza symptoms",
            "Nasal and sinus congestion relief",
            "Sneezing, watery eyes, and runny nose",
            "Minor body aches and fever relief"
        ],
        "general_uses_ar": [
            "تخفيف أعراض نزلات البرد والإنفلونزا",
            "تخفيف احتقان الأنف والجيوب الأنفية",
            "تخفيف العطس ورشح الأنف وإدماع العينين",
            "تسكين آلام الجسم وخفض الحمى"
        ],
        "standard_route": "Oral",
        "standard_route_ar": "عن طريق الفم"
    },
    "antinal": {
        "canonical_name": "Antinal",
        "generic_name": "Nifuroxazide",
        "active_ingredients": ["Nifuroxazide"],
        "drug_class": "Intestinal Antiseptic / Antibacterial",
        "what_is_it": "Antinal contains nifuroxazide, a broad-spectrum intestinal antiseptic that acts locally in the digestive tract with minimal systemic absorption.",
        "what_is_it_ar": "أنتينال يحتوي على نيفوروكسازيد، وهو مطهر معوي واسع المجال يعمل موضعياً داخل الجهاز الهضمي لعلاج الإسهال البكتيري دون امتصاص جهازي كبير.",
        "general_uses": [
            "Acute bacterial diarrhea of non-invasive origin",
            "Intestinal gastroenteritis and bacterial dysentery",
            "Colitis and intestinal infection management"
        ],
        "general_uses_ar": [
            "علاج الإسهال الحاد ذي المنشأ البكتيري",
            "النزلات المعوية والتهابات الأمعاء البكتيرية",
            "تطهير الجهاز الهضمي من البكتيريا المسببة للإسهال"
        ],
        "standard_route": "Oral",
        "standard_route_ar": "عن طريق الفم"
    },
    "flagyl": {
        "canonical_name": "Flagyl",
        "generic_name": "Metronidazole",
        "active_ingredients": ["Metronidazole"],
        "drug_class": "Nitroimidazole Antimicrobial / Antiprotozoal",
        "what_is_it": "Flagyl is an antimicrobial medication containing metronidazole that treats anaerobic bacterial infections and protozoal parasitic infections.",
        "what_is_it_ar": "فلاجيل يحتوي على مترونيدازول، وهو مضاد للميكروبات والطفيليات يقضي على البكتيريا اللاهوائية والطفيليات الأولية.",
        "general_uses": [
            "Protozoal infections such as amoebiasis, giardiasis, and trichomoniasis",
            "Anaerobic bacterial intra-abdominal infections",
            "Dental and periodontal abscesses",
            "Bacterial vaginosis"
        ],
        "general_uses_ar": [
            "العدوى الطفيلية مثل الأميبا والجيارديا والتريكوموناس",
            "عدوى البكتيريا اللاهوائية داخل البطن والحوض",
            "خراجات الأسنان والتهابات اللثة",
            "التهاب المهبل البكتيري"
        ],
        "standard_route": "Oral",
        "standard_route_ar": "عن طريق الفم"
    },
    "brufen": {
        "canonical_name": "Brufen",
        "generic_name": "Ibuprofen",
        "active_ingredients": ["Ibuprofen"],
        "drug_class": "Non-Steroidal Anti-Inflammatory Drug (NSAID)",
        "what_is_it": "Brufen is an anti-inflammatory and pain-relieving medication containing ibuprofen that reduces fever and inflammatory mediator synthesis.",
        "what_is_it_ar": "بروفين هو دواء مسكن ومضاد للالتهاب يحتوي على إيبوبروفين يعمل على خفض الحرارة وتخفيف الألم والالتهابات.",
        "general_uses": [
            "Inflammatory joint conditions and rheumatoid arthritis",
            "Musculoskeletal pain and backache",
            "Dental pain and postoperative swelling",
            "Fever reduction in inflammatory illnesses"
        ],
        "general_uses_ar": [
            "التهابات المفاصل والروماتيزم",
            "آلام العضلات والظهر والالتواءات",
            "آلام وتورمات الأسنان وما بعد العمليات",
            "تسكين الألم وخفض درجات الحرارة"
        ],
        "standard_route": "Oral",
        "standard_route_ar": "عن طريق الفم"
    },
    "voltaren": {
        "canonical_name": "Voltaren",
        "generic_name": "Diclofenac Sodium",
        "active_ingredients": ["Diclofenac Sodium"],
        "drug_class": "Non-Steroidal Anti-Inflammatory Drug (NSAID)",
        "what_is_it": "Voltaren contains diclofenac sodium, providing anti-inflammatory, analgesic, and antipyretic properties for severe or chronic inflammatory disorders.",
        "what_is_it_ar": "فولتارين يحتوي على ديكلوفيناك الصوديوم، وهو مضاد التهاب قوي ومسكن للألم يستخدم في الحالات الالتهابية الحادة والمزمنة.",
        "general_uses": [
            "Osteoarthritis, rheumatoid arthritis, and ankylosing spondylitis",
            "Acute gout attacks and renal colic pain",
            "Post-traumatic and postoperative inflammation"
        ],
        "general_uses_ar": [
            "خشونة المفاصل والتهاب المفاصل الروماتويدي والفقاري",
            "نوبات النقرس الحادة والمغص الكلوي",
            "تسكين الالتهابات والتورمات بعد الإصابات والعمليات"
        ],
        "standard_route": "Oral / Intramuscular",
        "standard_route_ar": "عن طريق الفم / حقن عضلي"
    },
    "omeprazole": {
        "canonical_name": "Omeprazole",
        "generic_name": "Omeprazole",
        "active_ingredients": ["Omeprazole"],
        "drug_class": "Proton Pump Inhibitor (PPI)",
        "what_is_it": "Omeprazole is a proton pump inhibitor that suppresses gastric acid secretion by specific inhibition of the H+/K+-ATPase enzyme system at the secretory surface of the gastric parietal cell.",
        "what_is_it_ar": "أوميبرازول هو مثبط لمضخة البروتون يقلل من إفراز حمض المعدة عن طريق تثبيط إنزيمات الخلايا الجدارية للمعدة.",
        "general_uses": [
            "Gastroesophageal reflux disease (GERD) and heartburn",
            "Gastric and duodenal peptic ulcers",
            "Eradication of Helicobacter pylori (in combination regimens)",
            "Prevention of NSAID-associated gastric ulcers"
        ],
        "general_uses_ar": [
            "علاج ارتجاع المريء وحرقة المعدة",
            "قرحة المعدة والاثني عشر",
            "المشاركة في علاج جرثومة المعدة (الهيليكوباكتر)",
            "الوقاية من تقرحات المعدة الناتجة عن المسكنات"
        ],
        "standard_route": "Oral",
        "standard_route_ar": "عن طريق الفم"
    },
    "septazole": {
        "canonical_name": "Septazole",
        "generic_name": "Sulfamethoxazole / Trimethoprim (Co-trimoxazole)",
        "active_ingredients": ["Sulfamethoxazole", "Trimethoprim"],
        "drug_class": "Sulfonamide and Dihydrofolate Reductase Inhibitor combination",
        "what_is_it": "Septazole contains a synergistic antibacterial combination blocking consecutive steps in bacterial folic acid synthesis.",
        "what_is_it_ar": "سيبتازول هو مضاد حيوي مركب يحتوي على سلفاميثوكسازول وتريميثوبريم يثبط تصنيع حمض الفوليك في البكتيريا.",
        "general_uses": [
            "Urinary tract bacterial infections",
            "Acute exacerbations of chronic bronchitis",
            "Pneumocystis jirovecii pneumonia prophylaxis and treatment",
            "Certain gastrointestinal bacterial infections"
        ],
        "general_uses_ar": [
            "عدوى المسالك البولية البكتيرية",
            "التهاب الشعب الهوائية المزمن الحاد",
            "الوقاية وعلاج بعض أنواع الالتهاب الرئوي الخاص",
            "بعض التهابات الجهاز الهضمي البكتيرية"
        ],
        "standard_route": "Oral",
        "standard_route_ar": "عن طريق الفم"
    },
    "ciprocin": {
        "canonical_name": "Ciprocin",
        "generic_name": "Ciprofloxacin",
        "active_ingredients": ["Ciprofloxacin Hydrochloride"],
        "drug_class": "Fluoroquinolone Antibacterial",
        "what_is_it": "Ciprocin contains ciprofloxacin, a broad-spectrum fluoroquinolone antibacterial that inhibits bacterial DNA gyrase and topoisomerase IV.",
        "what_is_it_ar": "سيبروسين يحتوي على سيبروفلوكساسين، وهو مضاد حيوي من عائلة الفلوروكينولون يثبط إنزيمات تضاعف الحمض النووي للبكتيريا.",
        "general_uses": [
            "Complicated urinary tract and kidney infections (pyelonephritis)",
            "Gastrointestinal and intra-abdominal bacterial infections",
            "Bone and joint bacterial infections",
            "Severe respiratory tract bacterial infections"
        ],
        "general_uses_ar": [
            "عدوى المسالك البولية المعقدة والتهاب الكلى",
            "عدوى الجهاز الهضمي والتهابات البطن البكتيرية",
            "عدوى العظام والمفاصل البكتيرية",
            "التهابات الجهاز التنفسي الشديدة"
        ],
        "standard_route": "Oral",
        "standard_route_ar": "عن طريق الفم"
    },
    "alphintern": {
        "canonical_name": "Alphintern",
        "generic_name": "Chymotrypsin / Trypsin",
        "active_ingredients": ["Chymotrypsin", "Trypsin"],
        "drug_class": "Proteolytic Enzyme Anti-inflammatory",
        "what_is_it": "Alphintern contains active proteolytic enzymes that accelerate the resorption of inflammatory edema and hematomas.",
        "what_is_it_ar": "ألفينترن يحتوي على إنزيمات محللة للبروتين تعمل على تسريع امتصاص التورم والارتشاح الالتهابي والتجمعات الدموية.",
        "general_uses": [
            "Post-traumatic and postoperative edema and swelling",
            "Dental and maxillofacial inflammatory swelling",
            "Pelvic and ENT inflammatory conditions"
        ],
        "general_uses_ar": [
            "علاج التورم والارتشاح بعد الإصابات والعمليات الجراحية",
            "تورمات الأسنان وجراحة الفم والفكين",
            "المساعدة في تقليل الالتهابات والتورمات في مختلف التخصصات"
        ],
        "standard_route": "Oral",
        "standard_route_ar": "عن طريق الفم"
    },
    "cidophage": {
        "canonical_name": "Cidophage",
        "generic_name": "Metformin Hydrochloride",
        "active_ingredients": ["Metformin Hydrochloride"],
        "drug_class": "Biguanide Antihyperglycemic",
        "what_is_it": "Cidophage contains metformin, an oral biguanide antihyperglycemic agent that improves glucose tolerance and reduces hepatic glucose production.",
        "what_is_it_ar": "سيدوفاج يحتوي على ميتفورمين، وهو دواء خافض لسكر الدم يعمل على زيادة حساسية الجسم للأنسولين وتقليل إنتاج الجلوكوز في الكبد.",
        "general_uses": [
            "Management of Type 2 diabetes mellitus",
            "Improving glycemic control in metabolic syndrome",
            "Polycystic ovary syndrome (PCOS) insulin resistance management"
        ],
        "general_uses_ar": [
            "تنظيم مستوى السكر في الدم لمرضى السكري من النوع الثاني",
            "تحسين حساسية الخلايا للأنسولين",
            "المساعدة في علاج متلازمة تكيس المبايض المرتبطة بمقاومة الأنسولين"
        ],
        "standard_route": "Oral",
        "standard_route_ar": "عن طريق الفم"
    },
    "controloc": {
        "canonical_name": "Controloc",
        "generic_name": "Pantoprazole Sodium",
        "active_ingredients": ["Pantoprazole Sodium"],
        "drug_class": "Proton Pump Inhibitor (PPI)",
        "what_is_it": "Controloc contains pantoprazole, a proton pump inhibitor that selectively reduces gastric acid production.",
        "what_is_it_ar": "كونترولوك يحتوي على بانتوبرازول، وهو مثبط لمضخة البروتون يقلل إفراز أحماض المعدة بدقة وكفاءة.",
        "general_uses": [
            "Erosive esophagitis associated with GERD",
            "Treatment and maintenance of healing for duodenal and gastric ulcers",
            "Zollinger-Ellison syndrome"
        ],
        "general_uses_ar": [
            "علاج التهاب المريء التآكلي وارتجاع المريء",
            "علاج قرحة المعدة والاثني عشر والوقاية من تكرارها",
            "علاج حالات فرط إفراز الحمض المعدي"
        ],
        "standard_route": "Oral / Intravenous",
        "standard_route_ar": "عن طريق الفم / حقن وريدي"
    }
}


class MedicationIndicationResolver:
    """Resolves verified pharmacological classes, descriptions, and common indications."""

    @classmethod
    def resolve_knowledge(cls, drug_name: str, generic_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve verified medication reference data by brand or generic name."""
        if not drug_name and not generic_name:
            return None

        # Try brand lookup
        search_keys = []
        if drug_name:
            search_keys.append(drug_name.strip().lower())
        if generic_name:
            search_keys.append(generic_name.strip().lower())

        for k in search_keys:
            # Direct key match
            if k in VERIFIED_MEDICATION_KNOWLEDGE:
                return VERIFIED_MEDICATION_KNOWLEDGE[k]

            # Partial match on constituent words
            for catalog_key, data in VERIFIED_MEDICATION_KNOWLEDGE.items():
                if catalog_key in k or k in catalog_key:
                    return data
                if generic_name and catalog_key in generic_name.lower():
                    return data

        return None
