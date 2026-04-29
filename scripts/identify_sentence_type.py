import ollama

def classify_sentences_with_reasoning(model_name, sentences):
    """
    Uses Chain-of-Thought prompting to minimize 'Date-Bias' and 'Procedural-Bias'.
    """
    
    system_prompt = (
        "You are a linguistic expert specializing in public administration reports. "
        "Your task is to classify sentences based on their SUBSTANTIVE intent.\n\n"
        
        "### DEFINITIONS & RULES:\n"
        "1. [POLICY]: Future intent or goals (e.g., 'will', 'aims', 'commits').\n"
        "2. [ACTION]: This is the key implementation category. It includes:\n"
        "   - Physical work (e.g., 'built', 'installed').\n"
        "   - Financial work (e.g., 'spent', 'allocated').\n"
        "   - GOVERNANCE OUTPUTS: If a council 'produced', 'finalized', or 'endorsed' "
        "     a specific plan, report, or framework, this is an ACTION.\n"
        "3. [NEUTRAL]: Administrative noise. Use this ONLY if there is no substantive "
        "project or document being created. Examples: meeting dates, greetings, "
        "personnel changes.\n\n"
        
        "### HANDLING DISTRACTORS:\n"
        "- Do not let 'Dates' (e.g., 8 July) or 'Committees' (e.g., Audit Committee) "
        "  trick you into a [NEUTRAL] tag if a document was produced or a task completed.\n\n"
        
        "### OUTPUT FORMAT:\n"
        "Reasoning: (Brief 1-sentence analysis of the primary verb and outcome)\n"
        "Category: [TAG]"
    )

    results = []
    for text in sentences:
        try:
            response = ollama.chat(
                model=model_name,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': f"Classify this: {text}"},
                ],
                options={'temperature': 0}
            )
            
            # Extract the content
            output = response['message']['content']
            
            # Simple logic to find the tag in the multi-line response
            tag = "[ERROR]"
            if "[POLICY]" in output.upper(): tag = "[POLICY]"
            elif "[ACTION]" in output.upper(): tag = "[ACTION]"
            elif "[NEUTRAL]" in output.upper(): tag = "[NEUTRAL]"
            
            results.append({"sentence": text, "label": tag, "reasoning": output})
            
        except Exception as e:
            results.append({"sentence": text, "label": f"ERROR", "reasoning": str(e)})
            
    return results

# --- Execution ---

# Test the improved logic
if __name__ == "__main__":
    #MODEL = "gemini-3-flash-preview:latest"
    MODEL = "gemma4:31b"
    test_cases = [
        "Adelaide Hills Regional Waste Management Authority Board Cr Christie Thornton 52 | Alexandrina Council Making and Reviewing Decisions Delegations Ombudsman SA Enquiries In 2024/25 Council responded to 12 enquiries from the SA Ombudsman relating to the following topics",
        "Alexandrina Council joined with the City of Victor Harbor to deliver a workshop for Council Members on public transport options on the Fleurieu Volunteer Recognition Event Enabled Peninsula",
        "Audit and Risk Committee Alexandrina Council’s Audit and Risk Committee is established under section 126 of the Local Government Act 1999",
        "Auditor Independence Land use code applied to Council Rates for property Council appointed Galpins Accountants, Auditors and Business Consultants as its external auditor on 1 July 2020 with a period of up to five (5) years",
        "Concept Plan Division (b) Proposed Nomination of Cr Lewis to the Libraries Board of SA (a) Committees of Council Cemeteries Advisory Committee Committees of Council are established under the Local Government Act 1999 (Act)",
        "Connected.’ and to thrive into the future It is a story developed with our community representing what we want Alexandrina to be like in 2040 and includes five objectives that Council will focus its efforts on",
        "Council Member Training and Development Non-Mandatory Training Date Training Provider All Council Members (Cr Craig Maidment apology) Set Up for Success David Spear, VUCA Pty Ltd Murray Darling Association 80th National General Conference and AGM Murray Darling Association Crs Milli Livingston & Michael Scott Alexandrina Council, City of Victor Harbor and District Council of Yankalilla All Council Members (Cr Peter Oliver apology) Joint Transport Workshop All Council Members (Cr Lou Nicholson and Cr Peter Oliver apology) Community Strategic Plan workshop Alexandrina Council Cr Lou Nicholson 28 to 30 August 2024 LGA Roads & Works Conference Local Government Association of SA Local Government Association of SA & Peats Composting & Brinkley Waste & Recycling Cr Bill Coomans LGA Waste & Recycling Tour Mayor Keith Parkes LGA AGM & Conference Local Government Association of SA Various dates, commencing 8 April 2025 and ongoing until further notice Alexandrina Council",
        "Council commenced background documentation for the Port Elliot and Waterport Local Heritage Code Amendment, while foundational work continued for the Middleton and Goolwa Local Heritage Code Amendments to support the identification and protection of places of local heritage significance.",
        "Council completed a review of the Alexandrina Business Services model including investigating the expansion of business services into the North and West Wards",
        "Council conducted a review of its Long Term Financial Plan (LTFP), Strategic Asset Management Plan (SAMP) and Community Strategic Plan",
        "Council delivered 20 community consultations, sent 10 My Say Alexandrina e-newsletters and regularly posted Council Meeting resolution updates on the My Say project site and in newsletters.",
        "Council explored actions and strategies to increase use of the Encounter Bikeway and other opportunities to increase active transport This included, the ‘Schools Open Street’ trial, which was undertaken in term 1 2025 at Port Elliot Primary School.",
        "Council has significantly improved recruitment and employee engagement through a more structured hiring process, enhanced internal resources, and a stronger focus on its employee value proposition",
        "Council joined the citizen science program, ‘Living Lightly Locally’, which helps deliver strategic sustainability actions across the both the Climate Emergency Action Plan and the Environmental Action Plan.",
        "Council provided input into the draft Greater Adelaide Regional Plan, which sets the broader framework for the future of the Fleurieu.",
        "Council secured Australian Government funding through the Local Road and Community Infrastructure Program to upgrade the Clayton Bay public toilet, addressing the lack of accessible facilities This project was completed in 2025.",  
        "Council signed three leases with the Friends of the PS Oscar W to formally hand over the day-to-day operations of our heritage-listed paddle steamer",
        "Council supported Family Daycare Programs (Department of Education) to deliver region-wide morning tea events to promote family daycare as a viable and rewarding career path",
        "Council supported community resilience by assisting local groups with disaster preparedness plans, training, and social connection events, including activating venues as support hubs",
        "Council supported the Hills and Fleurieu Local Food Future Project to deliver mental health awareness workshops with the Breakthrough Mental Health Research Foundation, reaching over 40 attendees and enabling 10 locals to complete Mental Health First Aid training",
        "Council supported the participation of a team in the annual Management Challenge This LGA simulation based team building, learning and networking program uses real local government themes, the types of issues that a senior management team in a council would most likely face",
        "Council worked with the City of Victor Harbor, headspace Victor Harbor, Goolwa Community Centre and local young volunteers, and supported by a Human Services SA grant to deliver the Fleurieu Block Parties series for SA Youth Week (April)",
        "Council’s joint venture, the Fleurieu Aquatic Centre, has identified that it undertakes significant business activities under the National Competition Policy and annually reviews the Fleurieu Aquatic Centre operations to ensure competitive neutrality is maintained",
        "During the 2024/25 financial year, the Committee met a total of seven (7) times to work through the eight key action themes listed within the Committee’s Work Plan: The role of the Advisory Group is to provide advice, feedback and advocacy with respect to future options for the Strathalbyn Recreation Precinct at Lot 10 Langhorne Creek Road, Strathalbyn under the care and control of Alexandrina Council.",
        "During the past financial year, Council met to consider information, reports and recommendations from Administration; to set budgets and arrive at decisions on strategies and policies to benefit the community",
        "Freedom of Information Office of the CEO The Freedom Information Statement is published by Alexandrina Council in accordance with the requirements of the Freedom of Information Act 1991",
        "In July 2024, Council introduced a new enterprise procurement software system which supports procurement planning, competitive tendering, evaluation, assessment, and contract processes with built in workflows, checklists and procedures resulting in consistent and controlled procurement practices",
        "In collaboration with Second Nature Conservancy (formerly known as Goolwa to Wellington Local Action Planning [GWLAP]), Council hosted several community workshops and a sold-out plant offer for residents providing 1,000 locally grown indigenous plants at a discounted rate.",
        "In order to commence a review, a Council is required to prepare a Representations Options Paper (Paper) which outlines the representation structures available",
        "In partnership with the Adelaide Hills Regional Waste Management Authority & KESAB, Council supported a behind-the-scenes tour of local waste and recycling facilities This event was hosted by KESAB with 11 residents attending"
    ]
    print("Running high-precision classification...\n")
    results = classify_sentences_with_reasoning(MODEL, test_cases)
    
    for r in results:
        print(f"{r['label']:<10} | {r['sentence']}")




