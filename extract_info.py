import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from langsmith import traceable

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


@traceable(name="extractInfo")
def extract_info(current_query):
    """Extract only caller-provided / factual incident information.

    Severity is deliberately NOT extracted here. It is derived separately
    from the merged incident state using assess_severity().
    """

    prompt = f"""
# Role
You are an expert real-time emergency incident data extractor.
Analyze only the latest caller message and extract factual incident information.

# Instructions
- Extract information only from explicit statements or very high-confidence inferences.
- If a field is not mentioned, unclear, incomplete, or possibly misheard, set it to "Unknown".
- Do not invent facts.
- Return exactly one valid JSON object.
- Do not return markdown, code fences, explanations, or extra text.

# Location Rules
- Accept only a clear and plausible address, area, landmark, street, city, or proper place name.
- Do not treat random words, broken phrases, or unclear sounds as locations.
- If the caller clearly corrects a location, extract the corrected location.
- Example: "It is not Vastrapur, it is Navrangpura" means location is "Navrangpura".
- If the correction is unclear or the new location does not sound like a legitimate place name, return "Unknown".
- Never guess or autocorrect an uncertain location.

# Fields to Extract
1. emergency_type:
   - The primary nature of the emergency, normalized to a short label (2-4 words).
   - Examples: "Fire", "Medical Emergency", "Road Traffic Accident", "Assault/Violence", "Gas Leak", "Structural Collapse", "Natural Disaster".
   - Use the closest-fitting label based on the caller's description.
   - If more than one distinct emergency is described, join them with " + ".

2. location:
   - Follow the location rules above.

3. people_involved:
   - Record the number of people involved and, if stated, their role/relation.
   - Examples: "3 - two adults and one child", "1 - driver".
   - If only a vague quantity is given, preserve it, e.g. "a few", "several", "a group".
   - Never invent an exact number.

4. injuries:
   - Record whatever injury information the caller actually provides: count, nature, seriousness, consciousness, breathing status, bleeding, entrapment, etc.
   - Examples:
       "2 injured"
       "2 injured - one unconscious, one with minor cuts"
       "1 injured - heavy bleeding"
   - IMPORTANT: an injury COUNT by itself is valid information. If the caller says "2 people are injured" but gives no injury type, return "2 injured" — NOT "Unknown".
   - If the caller explicitly says nobody is injured, return "None".
   - If injuries are not mentioned either way, return "Unknown".
   - Never diagnose a medical condition or infer an injury only from the emergency type.

# Required JSON Format
{{
    "emergency_type": "short label or Unknown",
    "location": "value or Unknown",
    "people_involved": "count/description or Unknown",
    "injuries": "available injury information, None, or Unknown"
}}

Latest caller message:
{current_query}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    return json.loads(response.output_text)


@traceable(name="assessSeverity")
def assess_severity(incident_info):
    """Derive severity from the accumulated factual incident state."""

    factual_info = {
      "emergency_type": incident_info.get("emergency_type", "Unknown"),
      "location": incident_info.get("location", "Unknown"),
      "people_involved": incident_info.get("people_involved", "Unknown"),
      "injuries": incident_info.get("injuries", "Unknown"),
    }

    incident_json = json.dumps(factual_info, ensure_ascii=False)

    prompt = f"""
# Role
You are an emergency incident severity assessor.

Evaluate the incident using ONLY the factual structured information supplied below.
The caller does not choose the severity. Do not rely on emotional tone, urgency words,
or a caller simply describing the situation as "serious", "critical", etc.

# Output
Return exactly one word:
Low
Medium
High
Critical
Unknown

# Assessment Rules
- Critical:
  Concrete life-threatening indicators are present, such as not breathing,
  unconscious/unresponsive, severe or uncontrolled bleeding, a person trapped
  in an active fire/collapse, or another clearly life-threatening condition.

- High:
  Serious injury or immediate ongoing danger is described but it is not clearly
  life-threatening. Examples include an active significant fire, ongoing violence,
  dangerous gas leak, serious injury while conscious, or a large number of injured
  people even when individual injury details are not available.

- Medium:
  Injuries are reported but no life-threatening/serious indicators are given,
  or the situation presents moderate risk. An injury count by itself can support
  Medium severity; do NOT require the caller to provide the exact injury type.
  Examples include "1 injured" or "2 injured" with no further condition stated,
  minor injuries, or a small contained fire.

- Low:
  No injuries are reported and no immediate danger is described.

- Unknown:
  There is not enough factual information to make a reasonable assessment.

# Additional Guidance
- Consider emergency type, number of people involved, number of people injured,
  injury condition (when available), and ongoing hazards together.
- Injury condition is useful but OPTIONAL. Do not return Unknown merely because
  the injury type is missing when an injury count is clearly known.
- Do not infer Critical only from the number of people involved.
- Prefer the most conservative category supported by the facts; do not exaggerate.

Incident information:
{incident_json}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    severity = response.output_text.strip()
    allowed = {"Low", "Medium", "High", "Critical", "Unknown"}

    return severity if severity in allowed else "Unknown"
