from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from dataclasses import asdict

from src.data.preprocessor import get_available_locations, get_catalog
from src.input.validator import validate_preferences
from src.engine.recommender import get_recommendations
from src.output.renderer import render_result
from src.config import validate_config

app = FastAPI(title="Zomato AI Recommendation API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load catalog lazily
try:
    _catalog = get_catalog()
    _locations = get_available_locations()
except Exception as e:
    _catalog = {}
    _locations = []

class RecommendRequest(BaseModel):
    location: str
    budget: str
    cuisine: Optional[str] = None
    min_rating: Optional[float] = None
    additional_preferences: Optional[str] = None

@app.get("/locations")
def get_locations():
    """Returns canonical list of neighborhood locations from Zomato dataset."""
    return _locations

@app.get("/cuisines")
def get_cuisines():
    """Returns a sorted list of unique cuisines present in the catalog."""
    cuisines_set = set()
    for r in _catalog.values():
        for c in r.cuisines:
            cuisines_set.add(c)
    return sorted(list(cuisines_set))

@app.post("/recommend")
def recommend(req: RecommendRequest):
    """
    Accepts preferences, validates them, runs recommendations,
    and returns display-ready formatted cards.
    """
    if not validate_config():
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY environment variable is not configured on the server."
        )

    cuisine_val = None if req.cuisine == "All Cuisines" or not req.cuisine else req.cuisine
    
    prefs, errors = validate_preferences(
        location=req.location,
        budget=req.budget,
        cuisine=cuisine_val,
        min_rating=req.min_rating,
        additional_preferences=req.additional_preferences,
        available_locations=_locations
    )
    if errors:
        raise HTTPException(status_code=400, detail=errors)

    try:
        result = get_recommendations(prefs, _catalog)
        rendered = render_result(result)
        return asdict(rendered)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
