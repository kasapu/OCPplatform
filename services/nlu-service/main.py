"""
OCP Platform - NLU Service
Natural Language Understanding service for intent and entity detection
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging
import os

from intent_classifier import IntentClassifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="OCP NLU Service",
    description="Natural Language Understanding for intent classification",
    version="1.0.0"
)

# Initialize intent classifier
classifier = None


@app.on_event("startup")
async def startup_event():
    """Load NLU model on startup"""
    global classifier
    logger.info("Starting NLU Service...")

    try:
        classifier = IntentClassifier()
        await classifier.load_or_train()
        logger.info("✓ NLU model loaded successfully")
    except Exception as e:
        logger.error(f"✗ Failed to load NLU model: {e}")
        # Don't fail startup, use fallback
        classifier = IntentClassifier()

    logger.info("NLU Service started successfully!")


# ============================================
# MODELS
# ============================================

class ParseRequest(BaseModel):
    """Request to parse text"""
    text: str
    language: str = "en-US"
    context: Optional[Dict[str, Any]] = {}


class Intent(BaseModel):
    """Intent detection result"""
    name: str
    confidence: float


class Entity(BaseModel):
    """Entity extraction result"""
    entity_type: str
    value: str
    confidence: float
    start_char: Optional[int] = None
    end_char: Optional[int] = None


class Sentiment(BaseModel):
    """Sentiment analysis result"""
    label: str  # positive, neutral, negative
    score: float


class ParseResponse(BaseModel):
    """NLU parsing result"""
    intent: Intent
    entities: List[Entity] = []
    sentiment: Optional[Sentiment] = None


# ============================================
# ENDPOINTS
# ============================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "OCP NLU Service",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    model_loaded = classifier is not None and classifier.is_trained

    return {
        "status": "healthy" if model_loaded else "degraded",
        "model_loaded": model_loaded,
        "model_type": "spacy_textcat" if model_loaded else "fallback"
    }


@app.post("/parse", response_model=ParseResponse)
async def parse_text(request: ParseRequest):
    """
    Parse text for intent and entities

    This is the main NLU endpoint that analyzes user input
    """
    if not classifier:
        raise HTTPException(status_code=503, detail="NLU model not loaded")

    try:
        logger.info(f"Parsing text: {request.text}")

        # Classify intent
        result = await classifier.classify(request.text, request.context)

        logger.info(f"Intent: {result['intent']['name']} ({result['intent']['confidence']:.2f})")

        return ParseResponse(
            intent=Intent(
                name=result["intent"]["name"],
                confidence=result["intent"]["confidence"]
            ),
            entities=[
                Entity(
                    entity_type=e["entity_type"],
                    value=e["value"],
                    confidence=e["confidence"],
                    start_char=e.get("start_char"),
                    end_char=e.get("end_char")
                )
                for e in result.get("entities", [])
            ],
            sentiment=Sentiment(
                label=result.get("sentiment", {}).get("label", "neutral"),
                score=result.get("sentiment", {}).get("score", 0.5)
            )
        )

    except Exception as e:
        logger.error(f"Error parsing text: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to parse text: {str(e)}")


@app.post("/train")
async def train_model():
    """
    Trigger model training

    Trains the NLU model on data from the database
    """
    if not classifier:
        raise HTTPException(status_code=503, detail="Classifier not initialized")

    try:
        logger.info("Starting model training...")
        await classifier.train()
        logger.info("Model training completed")

        return {
            "status": "success",
            "message": "Model trained successfully"
        }

    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@app.get("/intents")
async def list_intents():
    """List all supported intents"""
    if not classifier:
        raise HTTPException(status_code=503, detail="Classifier not initialized")

    return {
        "intents": classifier.get_intents(),
        "count": len(classifier.get_intents())
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
