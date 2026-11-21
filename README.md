# 🏛️ CivicLens – AI Triage for Citizen Complaints

> **Smart City Municipal Operations Powered by Multimodal Generative AI**  
> *Transforming unstructured, multilingual citizen grievances into prioritized, actionable municipal work orders.*

---

## 📌 Problem Statement
Municipal corporations receive thousands of unstructured citizen complaints daily via social media, portals, and helplines in multiple regional languages. Critical hazards (such as exposed live wires, major pipeline bursts, or open manholes) frequently get buried under cosmetic complaints, while duplicate reports clog field teams.

**CivicLens** solves this by providing:
1. **Multilingual AI Triage:** Accepts complaints in **English, ಕನ್ನಡ (Kannada), and हिन्दी (Hindi)** with optional photo evidence.
2. **Automated Classification & Severity Assessment:** Powered by Google's **Gemini 3.8 Flash** with guaranteed structured JSON extraction.
3. **Deterministic Municipal Routing:** Authoritative rule engine mapping complaints directly to responsible city departments.
4. **Duplicate Complaint Detection:** TF-IDF vectorization and cosine similarity preventing duplicate work orders without dropping citizen records.
5. **Explainable Civic Impact Score (0–100):** Transparent scoring factoring severity, estimated affected citizens, and proximity to schools and hospitals, clearly separating citizen-reported claims from officer-verified facts.
6. **Executive Officer Dashboard:** Interactive Plotly analytics, custom priority sorting (`Critical` ➔ `Low`), multi-facet filtering, and live status dispatch workflows.

---

## 🏗️ Architecture & Data Flow

```text
[Citizen Grievance] (English / Kannada / Hindi + Optional Photo + Impact Context)
        │
        ▼
[Gemini 3.8 Flash Multimodal Engine] ➔ Translates to English & extracts structured JSON
        │
        ▼
[Rule-Based Department Router] ➔ Authoritative legal department assignment
        │
        ▼
[TF-IDF Duplicate Detector] ➔ Checks similarity against active tickets (Flags matches)
        │
        ▼
[Civic Impact Scorer] ➔ Calculates explainable 0–100 urgency score & priority band
        │
        ▼
[SQLite Persistent Database] ➔ Stores complete record with sequential ID (CL-YYYYMMDD-XXXX)
        │
        ▼
[Municipal Officer Command Center] ➔ Real-time KPIs, Plotly charts, priority table & verification
```

---

## 🛠️ Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Frontend UI** | Streamlit | Responsive government-themed portal & dashboard |
| **Backend & Logic** | Python 3.10+ | Pure Python standard library & clean modular architecture |
| **AI Triage** | Google Gen AI SDK (`google-genai`) | Gemini 3.8 Flash multimodal structured JSON triage |
| **Database** | SQLite3 | Built-in lightweight persistent relational database |
| **Data Processing**| Pandas | Data transformations and DataFrame exports |
| **Duplicate Engine**| Scikit-Learn | TF-IDF Vectorizer + Cosine Similarity |
| **Visualizations** | Plotly Express | Interactive donut charts, severity bars, and workload analytics |
| **Configuration** | Python-Dotenv | Secure environment variable management |

---

## 🚀 Quick Start & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Shirish006/CivicLens.git
cd CivicLens
```

### 2. Set Up Virtual Environment
- **Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **macOS / Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Open `.env` and add your [Google AI Studio](https://aistudio.google.com/) API key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.8-flash
```

### 5. Launch CivicLens
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🧪 Sample Grievances for Testing

### 1. English (Roads - Critical)
- **Location:** `100 Feet Road, Near Metro Pillar 42, Indiranagar, Bengaluru`
- **Description:** `Massive pothole in the middle of the road after heavy rains. Two two-wheelers skidded this morning. Needs immediate asphalt patching before an accident happens.`

### 2. Kannada (Waste - High)
- **Location:** `5ನೇ ಕ್ರಾಸ್, ಮಲ್ಲೇಶ್ವರಂ, ಬೆಂಗಳೂರು`
- **Description:** `ರಸ್ತೆಯ ಬದಿಯಲ್ಲಿ ಕಸದ ತೊಟ್ಟಿ ತುಂಬಿ ತುಳುಕುತ್ತಿದ್ದು, ದುರ್ನಾತ ಬೀರುತ್ತಿದೆ ಮತ್ತು ಬೀದಿ ನಾಯಿಗಳ ಕಾಟ ಹೆಚ್ಚಾಗಿದೆ.`

### 3. Hindi (Drainage - Critical)
- **Location:** `गांधी चौक, मेन मार्केट रोड, सेक्टर 4`
- **Description:** `मुख्य सड़क पर सीवर का ढक्कन टूटा हुआ है और खुला पड़ा है। रात में कोई भी इसमें गिर सकता है। तुरंत बंद करवाएं।`

---

## 📊 Civic Impact Score Formula (0–100)

$$\text{Total Score} = \min(100, \, \text{Severity Pts} + \text{Population Pts} + \text{School Pts} + \text{Hospital Pts})$$

- **Severity Baseline:** `Critical (+70)` | `High (+50)` | `Medium (+30)` | `Low (+10)`
- **Population Impact:** `<10 (+3)` | `10-49 (+7)` | `50-199 (+11)` | `200+ (+15)`
- **Sensitive Proximity:** Near School `(+8)` | Near Hospital `(+7)`
- **Priority Bands:**
  - `70 – 100`: **URGENT** (Immediate dispatch)
  - `40 – 69`: **ELEVATED** (Within 24 hours)
  - `0 – 39`: **ROUTINE** (Standard maintenance queue)

---

## 🔒 Security & Privacy
- **Zero API Key Exposure:** API keys are never stored in client-side code, database tables, or Git repositories.
- **Strict `.gitignore`:** Excludes `.env`, SQLite databases (`civiclens.db`), and uploaded media files.
- **Fail-Safe Offline Mode:** If network connection or API quota fails, CivicLens seamlessly falls back to an offline multilingual keyword analyzer without crashing.

---

## 🔮 Future Roadmap
- [ ] **WhatsApp & SMS Bot:** Citizen grievance intake via WhatsApp voice notes and location pins.
- [ ] **Geospatial Heatmap:** Interactive Mapbox/Leaflet clustering of city hazard zones.
- [ ] **Field Crew Mobile Verification:** Real-time before-and-after photo verification by municipal field inspectors before closing tickets.
- [ ] **Automated SLA Escalation:** Auto-escalate unaddressed Critical tickets after 4 hours to zonal commissioners.

---

## 📄 License
Developed for Smart City Hackathons under the MIT License.
