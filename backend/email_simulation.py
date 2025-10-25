import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()  # Assicurati di avere OPENAI_API_KEY nelle env variables

def simulate_conversation(supplier: dict, buyer_requirements: dict) -> dict:
    conversation = []
    
    # 1. Generate initial outreach (ask whether the recipient is the right contact)
    outreach = f"""
    Subject: Inquiry: {buyer_requirements.get('product_description', '')[:50]}
    
    Hi {supplier.get('contact_name', '')},
    
    I'm reaching out from {buyer_requirements.get('company_name', '')} regarding our need for {buyer_requirements.get('product_description', '')}.
    
    Quick question: are you the right person to speak with about this request? If not, could you please forward me the email of the correct contact or reply with their contact email?
    
    Brief requirements:
    - Quantity: {buyer_requirements.get('quantity', '')}
    - Budget: {buyer_requirements.get('budget', '')}
    - Timeline: {buyer_requirements.get('timeline', '')}
    
    Best regards,
    {buyer_requirements.get('contact_name', '')}
    """
    conversation.append({"role": "buyer", "message": outreach})

    # 2. Simulate supplier response for hackathon: supplier says they are not the right contact and provides a new email
    #    For the demo we return a deterministic response: "No ... contact: nomenuovo@techsupply.com"
    simulated_reply = (
        f"Subject: RE: Inquiry: {buyer_requirements.get('product_description', '')}\n\n"
        f"Hello {buyer_requirements.get('contact_name', '')},\n\n"
        "Thank you for reaching out. No, I'm not the right person to handle this request. "
        "Please contact: nomenuovo@techsupply.com for further details.\n\n"
        "Best regards,\n"
        f"{supplier.get('contact_name', '')}\n{supplier.get('company_name', '')}"
    )
    conversation.append({"role": "supplier", "message": simulated_reply})

    # 3. Analyze supplier reply to determine if it's the decision maker and extract the correct contact email (if any)
    extraction_prompt = f"""
    You are an assistant that reads a single supplier reply and extracts two pieces of information as JSON.
    Input conversation:
    {json.dumps(conversation)}

    Return a JSON object ONLY (no other text) with these fields:
    - is_decision_maker: boolean  # true if the supplier says they are the right contact
    - contact_email: string|null  # the email of the correct contact if provided, otherwise null
    - reason: string  # short explanation of how you decided
    """

    extraction = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": extraction_prompt + "\nRespond ONLY with valid JSON."}]
    )

    content = extraction.choices[0].message.content or "{}"
    extracted = json.loads(content)

    # If supplier is not the decision maker but provided an email, instruct buyer to contact that email next
    next_action = None
    if not extracted.get('is_decision_maker') and extracted.get('contact_email'):
        next_action = {
            "action": "contact_new_email",
            "email": extracted['contact_email']
        }

    return {
        "supplier": supplier,
        "conversation": conversation,
        "extracted_info": extracted,
        "next_action": next_action
    }

# Esempio di utilizzo:
if __name__ == "__main__":
    # Dati di esempio
    supplier_example = {
        "company_name": "TechSupply Corp",
        "contact_name": "John Smith",
        "email": "john.smith@techsupply.com"
    }
    
    buyer_requirements_example = {
        "company_name": "Tacto Track",
        "contact_name": "Alice Johnson",
        "product_description": "High-performance semiconductors",
        "quantity": "1000 units",
        "budget": "$50,000",
        "timeline": "Q4 2025"
    }
    
    # Test della funzione
    result = simulate_conversation(supplier_example, buyer_requirements_example)
    print(json.dumps(result, indent=2))