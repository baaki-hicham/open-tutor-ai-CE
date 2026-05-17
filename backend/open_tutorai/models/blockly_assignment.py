# backend/open_tutorai/models/blockly_assignment.py
"""
Table en base de données pour stocker les exercices Blockly.
Remplace les exercices codés en dur dans blockly_service.py.
"""

import uuid
import json
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Text,
    DateTime,
    Boolean,
)
from sqlalchemy import types

from open_tutorai.models.database import Base


# ─── Type UUID compatible SQLite (dev) ET PostgreSQL (prod) ──────────────────
# Copié depuis blockly_submission.py qui fait déjà la même chose
class UUID(types.TypeDecorator):
    impl = types.String

    def process_bind_param(self, value, dialect):
        """Avant d'écrire en DB : convertit UUID → string"""
        if value is not None:
            return str(value)

    def process_result_value(self, value, dialect):
        """Après lecture depuis DB : retourne la string telle quelle"""
        if value is not None:
            return value


# ─── Modèle principal ─────────────────────────────────────────────────────────

class BlocklyAssignment(Base):
    """
    Un exercice Blockly.
    Peut être créé manuellement par un enseignant
    OU généré automatiquement par l'IA.
    """

    __tablename__ = "blockly_assignments"

    # ── Identifiant ──────────────────────────────────────────────────────────
    id = Column(
        UUID(),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # ── Contenu de l'exercice ─────────────────────────────────────────────────

    title = Column(String, nullable=False)
    # Exemple : "Calculer la somme des nombres pairs"

    description = Column(Text, nullable=False)
    # La consigne affichée à l'étudiant
    # Exemple : "Crée un programme qui affiche la somme de 1 à N"

    difficulty = Column(
        String,
        nullable=False,
        default="débutant",
    )
    # Valeurs possibles : "débutant", "intermédiaire", "avancé"

    # ── Blocs Blockly autorisés ───────────────────────────────────────────────
    # Stocké en JSON dans la DB (ex: '["controls_if", "math_arithmetic"]')
    # None = tous les blocs sont autorisés
    allowed_blocks_json = Column(Text, nullable=True)

    # ── Cas de test ───────────────────────────────────────────────────────────
    # Stocké en JSON dans la DB
    # Format : [{"inputs": {}, "expected_output": "...", "description": "..."}]
    test_cases_json = Column(Text, nullable=False, default="[]")

    # ── Indices pour l'étudiant ───────────────────────────────────────────────
    # Stocké en JSON dans la DB
    # Format : ["Pense à utiliser une boucle", "La variable doit s'appeler N"]
    hints_json = Column(Text, nullable=False, default="[]")

    # ── Score max ─────────────────────────────────────────────────────────────
    max_score = Column(Integer, nullable=False, default=100)

    # ── Lien avec le cours ────────────────────────────────────────────────────
    course_id = Column(String, nullable=True, index=True)
    # Permet de retrouver tous les exercices d'un cours donné

    due_date = Column(DateTime, nullable=True)
    # Date limite de rendu (optionnel)

    # ── Infos sur la génération IA ────────────────────────────────────────────
    generated_by_ai = Column(Boolean, nullable=False, default=False)
    # True si cet exercice a été créé par l'IA

    generation_prompt = Column(Text, nullable=True)
    # Le prompt exact envoyé à l'IA pour créer cet exercice
    # Utile pour rejouer/améliorer la génération

    ai_model_used = Column(String, nullable=True)
    # Exemple : "claude-sonnet-4-20250514"

    # ── Auteur ────────────────────────────────────────────────────────────────
    created_by = Column(String, nullable=False)
    # teacher_id si créé par un humain, "ai" si 100% automatique

    # ── Statut ────────────────────────────────────────────────────────────────
    is_published = Column(Boolean, nullable=False, default=False)
    # False = brouillon (l'étudiant ne voit pas encore l'exercice)
    # True  = publié (l'étudiant peut travailler dessus)

    is_active = Column(Boolean, nullable=False, default=True)
    # False = exercice archivé (suppression douce)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # ─── Méthodes utilitaires ─────────────────────────────────────────────────
    # Ces méthodes évitent de faire json.loads() partout dans le code

    def get_allowed_blocks(self) -> list[str] | None:
        """Retourne la liste des blocs autorisés, ou None si tous autorisés."""
        if self.allowed_blocks_json is None:
            return None
        return json.loads(self.allowed_blocks_json)

    def set_allowed_blocks(self, blocks: list[str] | None):
        """Sauvegarde la liste des blocs en JSON."""
        if blocks is None:
            self.allowed_blocks_json = None
        else:
            self.allowed_blocks_json = json.dumps(blocks, ensure_ascii=False)

    def get_test_cases(self) -> list[dict]:
        """Retourne la liste des cas de test."""
        return json.loads(self.test_cases_json)

    def set_test_cases(self, test_cases: list[dict]):
        """Sauvegarde les cas de test en JSON."""
        self.test_cases_json = json.dumps(test_cases, ensure_ascii=False)

    def get_hints(self) -> list[str]:
        """Retourne la liste des indices."""
        return json.loads(self.hints_json)

    def set_hints(self, hints: list[str]):
        """Sauvegarde les indices en JSON."""
        self.hints_json = json.dumps(hints, ensure_ascii=False)

    def to_dict(self) -> dict:
        """
        Convertit le modèle en dictionnaire prêt à être retourné par l'API.
        C'est ce format que blockly_service.py et le router utilisent.
        """
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "difficulty": self.difficulty,
            "allowed_blocks": self.get_allowed_blocks(),
            "test_cases": self.get_test_cases(),
            "hints": self.get_hints(),
            "max_score": self.max_score,
            "course_id": self.course_id,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "generated_by_ai": self.generated_by_ai,
            "is_published": self.is_published,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
        }

    def __repr__(self):
        return (
            f"<BlocklyAssignment id={self.id!r} "
            f"title={self.title!r} "
            f"generated_by_ai={self.generated_by_ai}>"
        )