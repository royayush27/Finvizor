from fastapi import APIRouter

from app.models.schemas import IndustryInfo

router = APIRouter(prefix="/api/industries", tags=["industries"])

INDUSTRIES = [
    IndustryInfo(key="Technology", icon="\U0001F4BB", description="Software, hardware, semiconductors, AI/ML companies"),
    IndustryInfo(key="Healthcare", icon="\U0001F3E5", description="Pharmaceuticals, biotech, medical devices, healthcare services"),
    IndustryInfo(key="Financials", icon="\U0001F3E6", description="Banks, insurance, investment firms, fintech"),
    IndustryInfo(key="Consumer Discretionary", icon="\U0001F6D2", description="Retail, automotive, entertainment, luxury goods"),
    IndustryInfo(key="Consumer Staples", icon="\U0001F34E", description="Food, beverages, household products, essential goods"),
    IndustryInfo(key="Energy", icon="⚡", description="Oil & gas, renewable energy, utilities"),
    IndustryInfo(key="Industrials", icon="\U0001F3ED", description="Manufacturing, aerospace, construction, logistics"),
    IndustryInfo(key="Materials", icon="\U0001F3D7", description="Mining, chemicals, construction materials"),
    IndustryInfo(key="Communication Services", icon="\U0001F4E1", description="Telecom, media, internet services"),
    IndustryInfo(key="Real Estate", icon="\U0001F3E2", description="REITs, property development, real estate services"),
    IndustryInfo(key="Utilities", icon="\U0001F4A1", description="Electric, gas, water utilities, renewable infrastructure"),
]


@router.get("", response_model=list[IndustryInfo])
def list_industries() -> list[IndustryInfo]:
    return INDUSTRIES
