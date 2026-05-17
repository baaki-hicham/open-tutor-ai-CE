# backend/schemas/blockly.py
"""
Schémas Pydantic pour le module Blockly.
Validation stricte des données entrantes et sortantes.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID


# ─── Requêtes (Input) ────────────────────────────────────────────────────────

class BlocklySubmitRequest(BaseModel):
    """Corps de requête pour la soumission d'un exercice Blockly."""
    assignment_id: str = Field(..., description="ID de l'exercice")
    python_code: str = Field(..., min_length=1, description="Code Python généré par Blockly")
    blocks_json: Optional[str] = Field(None, description="XML du workspace Blockly")

    @validator('python_code')
    def validate_python_code(cls, v):
        # Longueur max pour éviter les abus
        if len(v) > 50_000:
            raise ValueError("Code trop long (max 50 000 caractères)")
        return v.strip()

    @validator('blocks_json')
    def validate_blocks_json(cls, v):
        if v and len(v) > 200_000:
            raise ValueError("Workspace trop volumineux")
        return v


class BlocklyTestRequest(BaseModel):
    """Corps de requête pour tester du code sans soumission officielle."""
    python_code: str = Field(..., min_length=1, max_length=50_000)
    assignment_id: str
    blocks_json: Optional[str] = None


class BlocklySaveWorkspaceRequest(BaseModel):
    """Corps de requête pour sauvegarder un brouillon de workspace."""
    assignment_id: str
    blocks_json: str = Field(..., max_length=200_000)


# ─── Modèles internes ────────────────────────────────────────────────────────

class TestCase(BaseModel):
    """Définition d'un cas de test pour un exercice."""
    inputs: dict[str, Any] = Field(default_factory=dict)
    expected_output: str
    description: Optional[str] = None


class TestCaseResult(BaseModel):
    """Résultat d'un cas de test individuel."""
    index: int
    passed: bool
    expected: str
    got: str
    description: Optional[str] = None


class ExecutionResult(BaseModel):
    """Résultat de l'exécution du code Python en sandbox."""
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None
    execution_time_ms: float = 0
    timed_out: bool = False


# ─── Réponses (Output) ───────────────────────────────────────────────────────

class BlocklyTestResponse(BaseModel):
    """Réponse au test de code (sans soumission officielle)."""
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None
    test_results: Optional[List[TestCaseResult]] = None
    execution_time_ms: float = 0

    class Config:
        from_attributes = True


class BlocklySubmissionResponse(BaseModel):
    """Données d'une soumission dans l'historique."""
    id: UUID
    assignment_id: str
    assignment_title: Optional[str] = None
    python_code: str
    blocks_json: Optional[str] = None
    score: Optional[int] = None
    ai_feedback: Optional[str] = None
    submitted_at: datetime
    test_results: Optional[List[TestCaseResult]] = None

    class Config:
        from_attributes = True


class BlocklyAssignmentResponse(BaseModel):
    """Détails d'un exercice Blockly."""
    id: str
    title: str
    description: str
    allowed_blocks: Optional[List[str]] = None  # None = tous les blocs
    test_cases: List[TestCase] = []
    max_score: int = 100
    hints: List[str] = []
    course_id: Optional[str] = None
    due_date: Optional[datetime] = None

    class Config:
        from_attributes = True


class BlocklyProgressStats(BaseModel):
    """Statistiques de progression pour le dashboard."""
    total_submissions: int
    best_score: int
    average_score: float
    completed_assignments: int
    total_assignments: int
    last_activity: Optional[datetime] = None
    # ─────────────────────────────────────────────────────────────────────────────
# COLLE CES LIGNES À LA FIN DE : backend/open_tutorai/schemas/blockly.py
# (après la classe BlocklyProgressStats qui termine le fichier existant)
# ─────────────────────────────────────────────────────────────────────────────


# ─── Génération IA (nouveaux schémas) ─────────────────────────────────────────

class BlocklyGenerateRequest(BaseModel):
    """
    Corps de la requête POST /api/blockly/generate
    Envoyé par l'enseignant pour demander un exercice à l'IA.
    """

    theme: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Thème de l'exercice",
        examples=["boucles", "conditions", "listes", "fonctions"],
    )

    level: str = Field(
        "débutant",
        description="Niveau de difficulté",
        examples=["débutant", "intermédiaire", "avancé"],
    )

    objective: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Objectif pédagogique précis",
        examples=["afficher les nombres de 1 à N avec une boucle"],
    )

    course_id: Optional[str] = Field(
        None,
        description="ID du cours auquel rattacher l'exercice",
    )

    num_test_cases: int = Field(
        3,
        ge=1,
        le=10,
        description="Nombre de cas de test à générer",
    )

    allowed_blocks_hint: Optional[List[str]] = Field(
        None,
        description="Suggestion de blocs à utiliser (optionnel)",
        examples=[["controls_repeat_ext", "math_number", "text_print"]],
    )

    @validator("level")
    def validate_level(cls, v):
        valid = ["débutant", "intermédiaire", "avancé"]
        if v not in valid:
            raise ValueError(f"level doit être parmi : {valid}")
        return v

    @validator("theme")
    def validate_theme(cls, v):
        return v.strip()

    @validator("objective")
    def validate_objective(cls, v):
        return v.strip()


class BlocklyGenerateResponse(BaseModel):
    """
    Réponse du POST /api/blockly/generate
    Retourne l'exercice généré avec son ID en DB.
    """

    id: str
    title: str
    description: str
    difficulty: str
    allowed_blocks: Optional[List[str]] = None
    test_cases: List[TestCase]
    hints: List[str] = []
    max_score: int = 100
    course_id: Optional[str] = None
    generated_by_ai: bool = True
    is_published: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class BlocklyPublishRequest(BaseModel):
    """
    Corps de la requête POST /api/blockly/assignment/{id}/publish
    L'enseignant publie un exercice pour le rendre visible aux étudiants.
    """
    # Pas de champs : l'ID est dans l'URL, aucune donnée supplémentaire nécessaire
    pass


class BlocklyRegenerateRequest(BaseModel):
    """
    Corps de la requête POST /api/blockly/assignment/{id}/regenerate
    L'enseignant demande une nouvelle version avec un commentaire.
    """

    feedback: str = Field(
        "",
        max_length=500,
        description="Commentaire de l'enseignant pour améliorer l'exercice",
        examples=["Les cas de test sont trop simples", "Ajoute un cas avec N=0"],
    )