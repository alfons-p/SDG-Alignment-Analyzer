"""UN Sustainable Development Goals Definitions.

Contains comprehensive SDG data including:
- Official names and descriptions
- Local government keywords
- Target indicators
- Color codes for visualization

All 17 SDGs with detailed metadata for alignment analysis.
"""

from typing import Dict, Any, List

# UN Sustainable Development Goals Definitions
# Enhanced with comprehensive descriptions, local government keywords, and UN indicators
SDG_DEFINITIONS: Dict[int, Dict[str, Any]] = {
    1: {
        "name": "No Poverty",
        "short_description": "End poverty in all its forms everywhere",
        "description": "End poverty in all its forms everywhere by implementing nationally appropriate social protection systems and measures for all, including floors. Ensure that all men and women, in particular the poor and the vulnerable, have equal rights to economic resources, as well as access to basic services, ownership and control over land and other forms of property, inheritance, natural resources, appropriate new technology and financial services, including microfinance. Build the resilience of the poor and those in vulnerable situations and reduce their exposure and vulnerability to climate-related extreme events and other economic, social and environmental shocks and disasters.",
        "keywords": [
            "poverty", "income", "welfare", "social protection", "basic needs",
            "financial assistance", "economic support", "vulnerable populations",
            "low income", "disadvantaged", "equality", "social safety net",
            "poverty reduction", "living wage", "income support"
        ],
        "local_gov_keywords": [
            "rates assistance", "rates rebate", "pensioner rate relief", "financial hardship policy",
            "community grants", "community support fund", "hardship programs",
            "affordable housing", "social housing", "emergency accommodation",
            "food relief", "food bank", "community meals",
            "cost of living support", "utility relief", "energy bill assistance",
            "community welfare", "disability support services", "aged care services",
            "youth support", "homelessness services", "crisis support",
            "financial counseling", "money management programs", "emergency relief"
        ],
        "targets": ["1.1", "1.2", "1.3", "1.4", "1.5", "1.a", "1.b"],
        "indicators": [
            "Proportion of population below international poverty line",
            "Proportion of population living below national poverty lines",
            "Proportion of population covered by social protection floors",
            "Proportion of population with access to basic services",
            "Proportion of population with access to social protection systems"
        ],
        "color": "#E5243B"
    },
    2: {
        "name": "Zero Hunger",
        "short_description": "End hunger, achieve food security and improved nutrition and promote sustainable agriculture",
        "description": "End hunger, achieve food security and improved nutrition and promote sustainable agriculture. End all forms of malnutrition, including achieving internationally agreed targets on stunting and wasting in children under 5 years of age, and address the nutritional needs of adolescent girls, pregnant and lactating women and older persons. Ensure sustainable food production systems and implement resilient agricultural practices that increase productivity and production, that help maintain ecosystems, that strengthen capacity for adaptation to climate change, extreme weather, drought, flooding and other disasters and that progressively improve land and soil quality.",
        "keywords": [
            "hunger", "food security", "nutrition", "agriculture", "sustainable farming",
            "food access", "malnutrition", "food production", "local food",
            "community garden", "food waste", "healthy eating",
            "food systems", "sustainable food", "agricultural resilience"
        ],
        "local_gov_keywords": [
            "community garden", "community orchard", "urban farming", "allotment gardens",
            "food waste collection", "organic waste recycling", "composting program",
            "community kitchen", "school food program", "breakfast club",
            "food rescue", "food redistribution", "food share program",
            "farmers market", "local food hub", "food policy council",
            "sustainable catering", "council food procurement", "healthy food policy",
            "nutrition education", "cooking classes", "food literacy",
            "agricultural land management", "rural land use", "protecting farmland",
            "community meals program", "seniors meals", "Meals on Wheels",
            "emergency food relief", "food voucher program"
        ],
        "targets": ["2.1", "2.2", "2.3", "2.4", "2.5", "2.a", "2.b", "2.c"],
        "indicators": [
            "Prevalence of undernourishment",
            "Prevalence of moderate or severe food insecurity",
            "Prevalence of stunting in children under 5 years",
            "Prevalence of malnutrition",
            "Volume of production per labour unit by classes of farming"
        ],
        "color": "#DDA63A"
    },
    3: {
        "name": "Good Health and Well-being",
        "short_description": "Ensure healthy lives and promote well-being for all at all ages",
        "description": "Ensure healthy lives and promote well-being for all at all ages. Reduce the global maternal mortality ratio and end preventable deaths of newborns and children under 5 years of age. End the epidemics of AIDS, tuberculosis, malaria and neglected tropical diseases and combat hepatitis, water-borne diseases and other communicable diseases. Reduce by one third premature mortality from non-communicable diseases through prevention and treatment and promote mental health and well-being. Strengthen the prevention and treatment of substance abuse, including narcotic drug abuse and harmful use of alcohol. By 2020, halve the number of global deaths and injuries from road traffic accidents.",
        "keywords": [
            "health", "well-being", "mental health", "public health", "healthcare",
            "disease prevention", "healthy lifestyle", "wellness", "medical services",
            "health promotion", "community health", "health equity",
            "maternal health", "child health", "substance abuse"
        ],
        "local_gov_keywords": [
            "public health", "community health", "health promotion",
            "recreation center", "swimming pool", "fitness facilities",
            "parks and recreation", "active living", "walkability",
            "mental health services", "counseling services", "crisis support",
            "community health nurse", "health clinic", "medical services",
            "maternal and child health", "immunization", "vaccination",
            "chronic disease management", "health education", "wellness programs",
            "active transport", "cycling infrastructure", "walking paths",
            "sports facilities", "playing fields", "skate parks",
            "public toilets", "drinking water", "water fountains",
            "air quality monitoring", "pollution control", "environmental health"
        ],
        "targets": ["3.1", "3.2", "3.3", "3.4", "3.5", "3.6", "3.7", "3.8", "3.9", "3.a", "3.b", "3.c", "3.d"],
        "indicators": [
            "Maternal mortality ratio",
            "Under-5 mortality rate",
            "Mortality rate attributed to cardiovascular disease",
            "Suicide mortality rate",
            "Coverage of essential health services"
        ],
        "color": "#4C9F38"
    },
    4: {
        "name": "Quality Education",
        "short_description": "Ensure inclusive and equitable quality education and promote lifelong learning opportunities for all",
        "description": "Ensure inclusive and equitable quality education and promote lifelong learning opportunities for all. By 2030, ensure that all girls and boys complete free, equitable and quality primary and secondary education leading to relevant and effective learning outcomes. Ensure that all girls and boys have access to quality early childhood development, care and pre-primary education so that they are ready for primary education. Ensure equal access for all women and men to affordable and quality technical, vocational and tertiary education, including university. Substantially increase the number of youth and adults who have relevant skills, including technical and vocational skills, for employment, decent jobs and entrepreneurship.",
        "keywords": [
            "education", "learning", "school", "training", "literacy",
            "skill development", "educational quality", "inclusive education",
            "lifelong learning", "teacher training", "curriculum",
            "educational access", "vocational training", "higher education"
        ],
        "local_gov_keywords": [
            "public library", "library services", "reading programs", "literacy programs",
            "adult education", "community education", "Continuing Education",
            "vocational training", "skills training", "apprenticeships",
            "youth programs", "after school programs", "school holiday programs",
            "early childhood", "kindergarten", "preschool", "childcare",
            "student services", "educational support", "tutoring",
            "digital literacy", "computer training", "technology education",
            "arts education", "cultural programs", "music programs",
            "environmental education", "sustainability education",
            "community learning", "neighborhood houses", "learning centers",
            "scholarships", "educational grants", "study assistance"
        ],
        "targets": ["4.1", "4.2", "4.3", "4.4", "4.5", "4.6", "4.7", "4.a", "4.b", "4.c"],
        "indicators": [
            "Completion rate (primary, lower secondary, upper secondary)",
            "Participation rate in organized learning (one year before the official primary entry age)",
            "Participation rate in formal and non-formal education and training",
            "Proportion of population with proficiency levels in functional literacy"
        ],
        "color": "#C5192D"
    },
    5: {
        "name": "Gender Equality",
        "short_description": "Achieve gender equality and empower all women and girls",
        "description": "Achieve gender equality and empower all women and girls. End all forms of discrimination against all women and girls everywhere. Eliminate all forms of violence against all women and girls in the public and private spheres, including trafficking, sexual and other types of exploitation. Eliminate all harmful practices, such as child, early and forced marriage and female genital mutilation. Recognize and value unpaid care and domestic work through the provision of public services, infrastructure and social protection policies and the promotion of shared responsibility within the household and the family as nationally appropriate.",
        "keywords": [
            "gender equality", "women's rights", "gender equity", "female empowerment",
            "gender-based violence", "women's safety", "equal opportunity",
            "gender discrimination", "women's participation", "gender inclusion",
            "gender mainstreaming", "women's leadership", "girls' education"
        ],
        "local_gov_keywords": [
            "women's services", "women's center", "women's grants", "women's programs",
            "gender equity policy", "equal opportunity", "diversity and inclusion",
            "women in leadership", "gender balance", "women's representation",
            "domestic violence services", "women's shelter", "crisis support",
            "sexual assault services", "women's safety", "safe spaces",
            "parenting programs", "childcare services", "family support",
            "breastfeeding support", "maternal health", "women's health",
            "girls' programs", "young women", "youth programs for women",
            "women's employment", "women in business", "entrepreneurship support",
            "gender-aware planning", "gender impact assessment",
            "pay equity", "gender pay gap", "workplace equality"
        ],
        "targets": ["5.1", "5.2", "5.3", "5.4", "5.5", "5.6", "5.a", "5.b", "5.c"],
        "indicators": [
            "Whether or not legal frameworks are in place to promote, enforce and monitor equality and non‑discrimination",
            "Proportion of ever‑partnered women and girls aged 15 years and older subjected to physical, sexual or psychological violence",
            "Proportion of women and girls aged 15 years and older who undergo female genital mutilation",
            "Proportion of time spent on unpaid domestic and care work"
        ],
        "color": "#FF3A21"
    },
    6: {
        "name": "Clean Water and Sanitation",
        "short_description": "Ensure availability and sustainable management of water and sanitation for all",
        "description": "Ensure availability and sustainable management of water and sanitation for all. By 2030, achieve universal and equitable access to safe and affordable drinking water for all. By 2030, achieve access to adequate and equitable sanitation and hygiene for all and end open defecation, paying special attention to the needs of women and girls and those in vulnerable situations. By 2030, improve water quality by reducing pollution, eliminating dumping and minimizing release of hazardous chemicals and materials, halving the proportion of untreated wastewater and substantially increasing recycling and safe reuse globally.",
        "keywords": [
            "water", "sanitation", "water supply", "water quality", "water access",
            "sewage", "wastewater treatment", "water conservation", "water management",
            "clean water", "drinking water", "water infrastructure", "water reuse",
            "hygiene", "toilet access", "handwashing"
        ],
        "local_gov_keywords": [
            "water supply", "drinking water", "water treatment", "water quality",
            "sewerage", "wastewater", "sewage treatment", "stormwater",
            "drainage", "flood management", "water conservation", "water reuse",
            "recycled water", "greywater", "rainwater harvesting", "water savings",
            "toilets", "sanitation", "public toilets", "amenities",
            "handwashing", "hygiene facilities", "bathrooms",
            "water testing", "water monitoring", "water quality assurance",
            "water restrictions", "drought response", "water efficiency",
            "irrigation", "parks and gardens watering", "sports field irrigation"
        ],
        "targets": ["6.1", "6.2", "6.3", "6.4", "6.5", "6.6", "6.a", "6.b"],
        "indicators": [
            "Proportion of population using safely managed drinking water services",
            "Proportion of population using safely managed sanitation services",
            "Proportion of wastewater safely treated",
            "Proportion of population with access to safely managed drinking water services"
        ],
        "color": "#26BDE2"
    },
    7: {
        "name": "Affordable and Clean Energy",
        "short_description": "Ensure access to affordable, reliable, sustainable and modern energy for all",
        "description": "Ensure access to affordable, reliable, sustainable and modern energy for all. By 2030, ensure universal access to affordable, reliable and modern energy services. By 2030, increase substantially the share of renewable energy in the global energy mix. By 2030, double the global rate of improvement in energy efficiency. By 2030, enhance international cooperation to facilitate access to clean energy research and technology, including renewable energy, energy efficiency and advanced and cleaner fossil-fuel technology, and promote investment in energy infrastructure and clean energy technology.",
        "keywords": [
            "energy", "renewable energy", "clean energy", "energy access", "energy efficiency",
            "solar energy", "wind energy", "energy storage", "electricity",
            "energy sustainability", "energy security", "energy infrastructure",
            "affordable energy", "modern energy", "energy transition"
        ],
        "local_gov_keywords": [
            "solar panels", "solar power", "renewable energy", "green energy",
            "energy efficiency", "energy saving", "energy conservation",
            "LED lighting", "energy efficient buildings", "insulation",
            "energy audits", "energy management", "smart meters",
            "electric vehicle charging", "EV charging stations", "charging infrastructure",
            "street lighting", "solar street lights", "energy efficient lighting",
            "energy monitoring", "energy performance", "carbon neutral",
            "energy action plan", "energy strategy", "renewable energy target",
            "energy storage", "batteries", "energy grid", "distributed energy",
            "energy from waste", "waste to energy", "biomass energy"
        ],
        "targets": ["7.1", "7.2", "7.3", "7.a", "7.b"],
        "indicators": [
            "Proportion of population with access to electricity",
            "Proportion of population with primary reliance on clean fuels and technology",
            "Renewable energy share in the total final energy consumption",
            "Energy intensity measured in terms of primary energy and GDP"
        ],
        "color": "#FCC30B"
    },
    8: {
        "name": "Decent Work and Economic Growth",
        "short_description": "Promote sustained, inclusive and sustainable economic growth, full and productive employment and decent work for all",
        "description": "Promote sustained, inclusive and sustainable economic growth, full and productive employment and decent work for all. Sustain per capita economic growth in accordance with national circumstances and, in particular, at least 7 per cent gross domestic product growth per annum in the least developed countries. Achieve higher levels of economic productivity through diversification, technological upgrading and innovation, including through a focus on high-value added and labor-intensive sectors. Promote development-oriented policies that support productive activities, decent job creation, entrepreneurship, creativity and innovation, and encourage the formalization and growth of micro-, small- and medium-sized enterprises.",
        "keywords": [
            "economic growth", "employment", "decent work", "job creation", "economic productivity",
            "entrepreneurship", "business development", "workforce development",
            "economic development", "full employment", "productive employment",
            "labor rights", "fair work", "economic opportunity"
        ],
        "local_gov_keywords": [
            "economic development", "business development", "business support",
            "small business", "SMEs", "startups", "entrepreneurship",
            "business incubator", "business hub", "co-working space",
            "job creation", "employment programs", "workforce training",
            "skills development", "career development", "apprenticeships",
            "job placement", "employment services", "career counseling",
            "local employment", "buying local", "procurement",
            "economic strategy", "economic plan", "economic growth",
            "investment attraction", "business investment", "economic incentives",
            "tourism development", "visitor economy", "events",
            "market development", "export promotion", "industry development"
        ],
        "targets": ["8.1", "8.2", "8.3", "8.4", "8.5", "8.6", "8.7", "8.8", "8.9", "8.10", "8.a", "8.b"],
        "indicators": [
            "Annual growth rate of real GDP per capita",
            "Proportion of informal employment in non-agricultural employment",
            "Number of new businesses per 1,000 working-age persons",
            "Labour productivity (output per worker)",
            "Proportion of youth not in education, employment or training"
        ],
        "color": "#A21942"
    },
    9: {
        "name": "Industry, Innovation and Infrastructure",
        "short_description": "Build resilient infrastructure, promote inclusive and sustainable industrialization and foster innovation",
        "description": "Build resilient infrastructure, promote inclusive and sustainable industrialization and foster innovation. Develop quality, reliable, sustainable and resilient infrastructure, including regional and transborder infrastructure, to support economic development and human well-being, with a focus on affordable and equitable access for all. Promote inclusive and sustainable industrialization and, by 2030, significantly raise industry's share of employment and gross domestic product, doubling its share in the least developed countries.",
        "keywords": [
            "infrastructure", "innovation", "industrialization", "sustainable industry",
            "technology", "research and development", "industrial development",
            "infrastructure development", "innovation ecosystem", "digital infrastructure",
            "transport infrastructure", "communications technology", "innovation capacity"
        ],
        "local_gov_keywords": [
            "infrastructure", "roads", "bridges", "footpaths", "cycling paths",
            "public transport", "transport infrastructure", "traffic management",
            "digital infrastructure", "broadband", "internet", "wifi", "fibre",
            "innovation hub", "technology park", "business incubator",
            "research and development", "R&D", "innovation centre",
            "smart city", "digital services", "online services",
            "infrastructure planning", "capital works", "major projects",
            "industrial estate", "industrial development", "business park",
            "community infrastructure", "public facilities", "shared facilities",
            "maintenance", "asset management", "infrastructure renewal"
        ],
        "targets": ["9.1", "9.2", "9.3", "9.4", "9.5", "9.a", "9.b", "9.c"],
        "indicators": [
            "Proportion of the rural population who live within 2 km of an all-season road",
            "Manufacturing value added as a proportion of GDP",
            "Proportion of small-scale industries with a loan or line of credit",
            "Research and development expenditure as a proportion of GDP"
        ],
        "color": "#FD6925"
    },
    10: {
        "name": "Reduced Inequalities",
        "short_description": "Reduce inequality within and among countries",
        "description": "Reduce inequality within and among countries. By 2030, progressively achieve and sustain income growth of the bottom 40 per cent of the population at a rate higher than the national average. By 2030, empower and promote the social, economic and political inclusion of all, irrespective of age, sex, disability, race, ethnicity, origin, religion or economic or other status. Ensure equal opportunity and reduce inequalities of outcome, including by eliminating discriminatory laws, policies and practices and promoting appropriate legislation, policies and action in this regard.",
        "keywords": [
            "inequality", "social inclusion", "economic equality", "reducing disparities",
            "inclusive development", "social equity", "equal opportunity",
            "inequality reduction", "social justice", "marginalized groups",
            "vulnerable populations", "social protection", "inclusive growth"
        ],
        "local_gov_keywords": [
            "social inclusion", "inclusion", "accessibility", "diversity",
            "multicultural services", "multicultural programs", "diversity and inclusion",
            "accessible services", "universal access", "disability access",
            "aged services", "seniors services", "youth services", "child services",
            "indigenous services", "aboriginal services", "cultural services",
            "migrant services", "refugee services", "new migrant support",
            "disability services", "special needs", "inclusive programs",
            "community grants", "equity programs", "affordable services",
            "social housing", "community housing", "assistance programs",
            "welfare support", "hardship programs", "emergency relief",
            "advocacy", "community engagement", "participation"
        ],
        "targets": ["10.1", "10.2", "10.3", "10.4", "10.5", "10.6", "10.7", "10.a", "10.b", "10.c"],
        "indicators": [
            "Growth rates of household expenditure or income per capita",
            "Proportion of people living below 50 per cent of median income",
            "Proportion of the population reporting discrimination",
            "Gini coefficient",
            "Proportion of seats held by women in national parliaments"
        ],
        "color": "#DD1367"
    },
    11: {
        "name": "Sustainable Cities and Communities",
        "short_description": "Make cities and human settlements inclusive, safe, resilient and sustainable",
        "description": "Make cities and human settlements inclusive, safe, resilient and sustainable. By 2030, ensure access for all to adequate, safe and affordable housing and basic services and upgrade slums. By 2030, provide access to safe, affordable, accessible and sustainable transport systems for all, improving road safety, notably by expanding public transport, with special attention to the needs of those in vulnerable situations, women, children, persons with disabilities and older persons. By 2030, significantly reduce the adverse per capita environmental impact of cities, including by paying special attention to air quality and municipal and other waste management.",
        "keywords": [
            "urban development", "sustainable cities", "urban planning", "housing",
            "public transport", "urban infrastructure", "sustainable urbanism",
            "urban sustainability", "city planning", "transport systems",
            "urban resilience", "green cities", "smart cities", "inclusive cities"
        ],
        "local_gov_keywords": [
            "urban planning", "planning", "zoning", "development", "building",
            "housing", "affordable housing", "social housing", "residential development",
            "public transport", "bus", "train", "tram", "light rail", "public transit",
            "roads", "footpaths", "cycling", "walkability", "active transport",
            "parks", "playgrounds", "public spaces", "community spaces",
            "recreation", "sports facilities", "library", "community center",
            "urban design", "streetscapes", "public realm", "town centre",
            "heritage", "historic", "conservation", "cultural heritage",
            "sustainable transport", "electric vehicles", "EV charging",
            "climate action", "climate adaptation", "climate resilience",
            "urban growth", "population growth", "infrastructure planning"
        ],
        "targets": ["11.1", "11.2", "11.3", "11.4", "11.5", "11.6", "11.7", "11.a", "11.b", "11.c"],
        "indicators": [
            "Proportion of urban population living in slums",
            "Proportion of population that has convenient access to public transport",
            "Number of deaths, missing persons and directly affected persons attributed to disasters",
            "Proportion of household income spent on housing"
        ],
        "color": "#FD6925"
    },
    12: {
        "name": "Responsible Consumption and Production",
        "short_description": "Ensure sustainable consumption and production patterns",
        "description": "Ensure sustainable consumption and production patterns. Implement the 10-year framework of programmes on sustainable consumption and production, with all countries taking action, with developed countries taking the lead, taking into account the development and capabilities of developing countries. By 2030, achieve the sustainable management and efficient use of natural resources. By 2030, reduce waste generation through prevention, reduction, recycling and reuse. Support developing countries to strengthen their scientific and technological capacity to move towards more sustainable patterns of consumption and production.",
        "keywords": [
            "sustainable consumption", "sustainable production", "waste reduction",
            "resource efficiency", "circular economy", "waste management",
            "recycling", "sustainable materials", "responsible consumption",
            "eco-efficiency", "sustainable practices", "waste minimization"
        ],
        "local_gov_keywords": [
            "waste", "recycling", "waste reduction", "waste minimization", "waste management",
            "recycling", "recycling centre", "recycling depot", "materials recovery",
            "organic waste", "food waste", "green waste", "compost", "composting",
            "waste collection", "kerbside collection", "waste audit", "waste strategy",
            "circular economy", "re-use", "repair", "upcycling", "waste to energy",
            "landfill", "waste diversion", "zero waste", "waste avoidance",
            "sustainable procurement", "procurement policy", "buying guidelines",
            "single use plastics", "plastic reduction", "plastic free",
            "sustainable products", "eco-friendly", "environmentally friendly",
            "resource efficiency", "energy efficiency", "water efficiency",
            "sustainable events", "event waste", "sustainable operations"
        ],
        "targets": ["12.1", "12.2", "12.3", "12.4", "12.5", "12.6", "12.7", "12.8", "12.a", "12.b", "12.c"],
        "indicators": [
            "Number of countries with sustainable consumption and production (SCP) national action plans",
            "Material footprint",
            "Food waste index",
            "Proportion of hazardous waste treated"
        ],
        "color": "#BF8B2E"
    },
    13: {
        "name": "Climate Action",
        "short_description": "Take urgent action to combat climate change and its impacts",
        "description": "Take urgent action to combat climate change and its impacts. Strengthen resilience and adaptive capacity to climate-related hazards and natural disasters in all countries. Integrate climate change measures into national policies, strategies and planning. Improve education, awareness-raising and human and institutional capacity on climate change mitigation, adaptation, impact reduction and early warning. Implement the commitment undertaken by developed-country parties to the United Nations Framework Convention on Climate Change to a goal of mobilizing jointly $100 billion annually by 2020 from all sources to address the needs of developing countries.",
        "keywords": [
            "climate change", "climate action", "climate mitigation", "climate adaptation",
            "emissions reduction", "carbon emissions", "climate resilience",
            "climate impact", "climate policy", "climate strategy", "climate emergency",
            "global warming", "climate crisis", "climate solutions"
        ],
        "local_gov_keywords": [
            "climate change", "climate action", "climate strategy", "climate plan",
            "emissions reduction", "carbon reduction", "net zero", "carbon neutral",
            "greenhouse gas", "carbon emissions", "carbon footprint",
            "renewable energy", "clean energy", "solar", "wind", "energy efficiency",
            "climate adaptation", "climate resilience", "climate mitigation",
            "climate emergency", "climate action plan", "emissions target",
            "climate risk", "flood management", "drought response", "heat waves",
            "climate impact", "sea level rise", "extreme weather",
            "climate education", "community engagement", "climate awareness",
            "green infrastructure", "urban forest", "tree planting", "revegetation"
        ],
        "targets": ["13.1", "13.2", "13.3", "13.a", "13.b"],
        "indicators": [
            "Number of deaths, missing persons and directly affected persons attributed to disasters per 100,000 people",
            "Number of countries with national and local disaster risk reduction strategies",
            "Strengthening of capacity for climate change planning and management"
        ],
        "color": "#3F7E44"
    },
    14: {
        "name": "Life Below Water",
        "short_description": "Conserve and sustainably use the oceans, seas and marine resources for sustainable development",
        "description": "Conserve and sustainably use the oceans, seas and marine resources for sustainable development. By 2025, prevent and significantly reduce marine pollution of all kinds, in particular from land-based activities, including marine debris and nutrient pollution. By 2020, sustainably manage and protect marine and coastal ecosystems to avoid significant adverse impacts, including by strengthening their resilience, and take action for their restoration in order to achieve healthy and productive oceans. Minimize and address the impacts of ocean acidification, including through enhanced scientific cooperation at all levels.",
        "keywords": [
            "oceans", "marine", "marine life", "marine conservation", "coastal",
            "marine ecosystems", "ocean conservation", "sustainable fishing",
            "marine pollution", "ocean acidification", "blue economy",
            "marine biodiversity", "marine resources", "coastal management"
        ],
        "local_gov_keywords": [
            "marine", "coastal", "coast", "beach", "waterways", "estuary",
            "marine environment", "coastal management", "coastal erosion",
            "coastal protection", "coastal planning", "foreshore",
            "marine pollution", "water quality", "stormwater", "discharge",
            "marine conservation", "marine protected area", "coastal reserve",
            "wetlands", "saltmarsh", "seagrass", "mangroves",
            "fishing", "recreational fishing", "sustainable fishing",
            "marine education", "coastal education", "environmental education",
            "coastal access", "public access", "coastal facilities",
            "coastal infrastructure", "coastal community"
        ],
        "targets": ["14.1", "14.2", "14.3", "14.4", "14.5", "14.6", "14.7", "14.a", "14.b", "14.c"],
        "indicators": [
            "Marine plastic debris",
            "Coastal eutrophication",
            "Fish stocks within sustainable levels",
            "Proportion of fish stocks within biologically sustainable levels"
        ],
        "color": "#0A97D9"
    },
    15: {
        "name": "Life on Land",
        "short_description": "Protect, restore and promote sustainable use of terrestrial ecosystems, sustainably manage forests, combat desertification, and halt and reverse land degradation and halt biodiversity loss",
        "description": "Protect, restore and promote sustainable use of terrestrial ecosystems, sustainably manage forests, combat desertification, and halt and reverse land degradation and halt biodiversity loss. By 2020, ensure the conservation, restoration and sustainable use of terrestrial and inland freshwater ecosystems and their services, in particular forests, wetlands, mountains and drylands, in line with obligations under international agreements. By 2030, ensure the conservation of mountain ecosystems, including their biodiversity, in order to enhance their capacity to provide benefits that are essential for sustainable development.",
        "keywords": [
            "biodiversity", "ecosystems", "conservation", "forest", "wildlife",
            "terrestrial ecosystems", "land conservation", "biodiversity conservation",
            "habitat protection", "species protection", "environmental conservation",
            "sustainable land use", "land restoration", "reforestation"
        ],
        "local_gov_keywords": [
            "parks", "national park", "nature reserve", "conservation", "biodiversity",
            "wildlife", "habitat", "native vegetation", "revegetation", "planting",
            "tree planting", "urban forest", "green infrastructure", "corridors",
            "environmental conservation", "land conservation", "nature conservation",
            "ecosystem", "wetlands", "woodland", "forest", "trees",
            "flora", "fauna", "native species", "threatened species",
            "environmental protection", "environmental management", "bushcare",
            "landcare", "sustainable land management", "land rehabilitation",
            "environmental restoration", "ecological restoration", "weed management",
            "pest management", "environmental monitoring", "environmental planning"
        ],
        "targets": ["15.1", "15.2", "15.3", "15.4", "15.5", "15.6", "15.7", "15.8", "15.9", "15.a", "15.b", "15.c"],
        "indicators": [
            "Proportion of important sites for terrestrial and freshwater biodiversity that are covered by protected areas",
            "Proportion of forest area",
            "Proportion of land that is degraded over total land area",
            "Number of countries that have adopted relevant national legislation"
        ],
        "color": "#56C02B"
    },
    16: {
        "name": "Peace, Justice and Strong Institutions",
        "short_description": "Promote peaceful and inclusive societies for sustainable development, provide access to justice for all and build effective, accountable and inclusive institutions at all levels",
        "description": "Promote peaceful and inclusive societies for sustainable development, provide access to justice for all and build effective, accountable and inclusive institutions at all levels. Significantly reduce all forms of violence and related death rates everywhere. End abuse, exploitation, trafficking and all forms of violence against and torture of children. Promote the rule of law at the national and international levels and ensure equal access to justice for all. By 2030, provide legal identity for all, including birth registration.",
        "keywords": [
            "governance", "rule of law", "justice", "institutions", "peace",
            "human rights", "inclusive governance", "democratic participation",
            "institutional effectiveness", "accountability", "transparency",
            "corruption reduction", "public safety", "peaceful society"
        ],
        "local_gov_keywords": [
            "governance", "council", "council services", "customer service",
            "democracy", "participation", "community engagement", "consultation",
            "transparency", "accountability", "open government", "public accountability",
            "integrity", "ethics", "code of conduct", "fraud prevention",
            "justice", "legal services", "access to justice", "dispute resolution",
            "mediation", "ombudsman", "complaints", "feedback", "public participation",
            "community consultation", "stakeholder engagement", "inclusion",
            "accessibility", "universal access", "information access", "FOI", "freedom of information",
            "public safety", "emergency management", "disaster management",
            "law enforcement", "police", "safety", "security", "crime prevention",
            "good governance", "effective governance", "institutional capacity"
        ],
        "targets": ["16.1", "16.2", "16.3", "16.4", "16.5", "16.6", "16.7", "16.8", "16.9", "16.10", "16.a", "16.b"],
        "indicators": [
            "Number of victims of intentional homicide per 100,000 people",
            "Children aged 1-17 years who experienced physical punishment",
            "Unsentenced detainees as a proportion of overall prison population",
            "Proportion of the population who believe decision-making is inclusive and responsive"
        ],
        "color": "#00689D"
    },
    17: {
        "name": "Partnerships for the Goals",
        "short_description": "Strengthen the means of implementation and revitalize the global partnership for sustainable development",
        "description": "Strengthen the means of implementation and revitalize the global partnership for sustainable development. Finance: Develop a universal, rules-based, non-discriminatory and open multilateral trading system under the World Trade Organization, including through the conclusion of negotiations under its Doha Development Agenda. Significantly increase the exports of developing countries, in particular with a view to doubling the least developed countries' share of global exports by 2020. Realize full implementation of official development assistance commitments, including the commitment by many developed countries to achieve the target of 0.7 per cent of gross national income for official development assistance.",
        "keywords": [
            "partnership", "collaboration", "cooperation", "multi-stakeholder",
            "sustainable development", "global partnership", "knowledge sharing",
            "capacity building", "technology transfer", "resource mobilization",
            "implementation", "support mechanisms", "enabling environment"
        ],
        "local_gov_keywords": [
            "partnership", "collaboration", "cooperation", "partnerships",
            "stakeholder engagement", "partnerships", "strategic partnerships",
            "regional cooperation", "intergovernmental cooperation",
            "community partnerships", "sector partnerships", "cross-sector",
            "collaboration", "working together", "joint initiatives",
            "partnership framework", "memorandum of understanding", "MOU",
            "regional collaboration", "state government", "federal government",
            "community groups", "non-profit", "NGO", "volunteers",
            "private sector", "business partnerships", "industry partnerships",
            "academic partnerships", "research partnerships", "knowledge sharing",
            "capacity building", "training", "professional development",
            "networking", "best practice", "learning", "innovation network"
        ],
        "targets": ["17.1", "17.2", "17.3", "17.4", "17.5", "17.6", "17.7", "17.8", "17.9", "17.10", "17.11", "17.12", "17.13", "17.14", "17.15", "17.16", "17.17", "17.18", "17.19", "17.a", "17.b", "17.c"],
        "indicators": [
            "Net official development assistance as a proportion of OECD DAC donors' gross national income",
            "Proportion of countries receiving official development assistance",
            "Total resource flows for development",
            "Proportion of countries with comprehensive national development finance frameworks"
        ],
        "color": "#19486A"
    },
}