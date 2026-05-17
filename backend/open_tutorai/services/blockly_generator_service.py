# backend/open_tutorai/services/blockly_generator_service.py
"""
Service de génération automatique d'exercices Blockly via Ollama.
Utilise exactement le même système Ollama que blockly_service.py
(requests.post sur http://localhost:11434)
"""

import json
import logging
import requests
from datetime import datetime
from typing import AsyncGenerator
from sqlalchemy.orm import Session

from open_tutorai.models.blockly_assignment import BlocklyAssignment

logger = logging.getLogger(__name__)

# ─── Config Ollama ────────────────────────────────────────────────────────────
OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:0.5b"   # même modèle que blockly_service.py

# ─── Blocs Blockly valides ────────────────────────────────────────────────────
VALID_BLOCKLY_BLOCKS = [
    "controls_if", "controls_ifelse", "controls_repeat_ext",
    "controls_whileUntil", "controls_for", "controls_forEach",
    "controls_flow_statements", "logic_compare", "logic_operation",
    "logic_negate", "logic_boolean", "math_number", "math_arithmetic",
    "math_single", "math_modulo", "math_round", "math_on_list",
    "math_random_int", "text", "text_print", "text_join", "text_length",
    "lists_create_empty", "lists_create_with", "lists_length",
    "lists_getIndex", "lists_setIndex", "variables_get", "variables_set",
    "procedures_defnoreturn", "procedures_defreturn",
    "procedures_callnoreturn", "procedures_callreturn",
]

# ─── Prompt système ───────────────────────────────────────────────────────────
SYSTEM_PROMPT = f"""Tu es un expert pédagogique en programmation Blockly.
Tu crées des exercices pour une plateforme éducative.

RÈGLES ABSOLUES :
1. Réponds UNIQUEMENT avec un objet JSON valide, rien d'autre.
2. Zéro texte avant ou après le JSON. Zéro balise ```json```.
3. Les allowed_blocks doivent être dans cette liste :
   {json.dumps(VALID_BLOCKLY_BLOCKS)}
4. expected_output = ce que print() affiche exactement.
5. Les cas de test vont du plus simple au plus complexe.

FORMAT JSON EXACT :
{{
  "title": "Titre court",
  "description": "Consigne claire avec exemple. ex: si N=3, affiche 6",
  "difficulty": "débutant",
  "allowed_blocks": ["controls_repeat_ext", "math_number", "text_print"],
  "test_cases": [
    {{
      "inputs": {{}},
      "expected_output": "1\\n2\\n3",
      "description": "Affiche les nombres de 1 à 3"
    }}
  ],
  "hints": [
    "Indice vague pour démarrer",
    "Indice plus précis",
    "Indice quasi-solution"
  ]
}}

RÈGLES PÉDAGOGIQUES :
- débutant      : 2-3 blocs, 1 concept, 2 cas de test
- intermédiaire : 4-6 blocs, combinaison, 3 cas de test
- avancé        : 6+ blocs, algorithme complet, 4 cas de test"""


class BlocklyGeneratorService:
    def __init__(self, db: Session):
        self.db = db

    # ── Méthode principale ────────────────────────────────────────────────────

    async def generate_and_save(
        self,
        theme: str,
        level: str,
        objective: str,
        teacher_id: str,
        course_id: str | None = None,
        num_test_cases: int = 3,
        allowed_blocks_hint: list[str] | None = None,
    ) -> BlocklyAssignment:
        """Génère un exercice via Ollama et le sauvegarde en DB."""

        prompt = self._build_prompt(
            theme, level, objective, num_test_cases, allowed_blocks_hint
        )
        logger.info(f"Génération exercice — thème: {theme}, niveau: {level}")

        raw           = self._call_ollama(prompt)
        exercise_data = self._parse_response(raw)
        self._validate(exercise_data)

        assignment = self._save_to_db(
            exercise_data     = exercise_data,
            teacher_id        = teacher_id,
            course_id         = course_id,
            generation_prompt = prompt,
        )
        logger.info(f"Exercice sauvegardé — id: {assignment.id}")
        return assignment

    # ── Streaming pour l'UX enseignant ───────────────────────────────────────

    async def generate_stream(
        self,
        theme: str,
        level: str,
        objective: str,
        num_test_cases: int = 3,
    ) -> AsyncGenerator[str, None]:
        """
        Appelle Ollama en streaming et yield les chunks.
        Même logique que generate_feedback_stream dans blockly_service.py.
        """
        prompt = self._build_prompt(theme, level, objective, num_test_cases)

        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model"  : OLLAMA_MODEL,
                    "prompt" : f"{SYSTEM_PROMPT}\n\nUtilisateur : {prompt}",
                    "stream" : True,
                    "options": {"temperature": 0.7, "num_predict": 1000},
                },
                stream=True,
                timeout=120,
            )
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode("utf-8"))
                        if "response" in data:
                            yield data["response"]
                        if data.get("done"):
                            break
                    except Exception:
                        continue
        except Exception as e:
            yield f"ERREUR:{str(e)}"

    # ── Regénérer avec commentaire ────────────────────────────────────────────

    async def regenerate(
        self,
        assignment_id: str,
        teacher_id: str,
        feedback: str = "",
    ) -> BlocklyAssignment:
        """Regénère un exercice existant en tenant compte du commentaire."""

        original = self.db.query(BlocklyAssignment).filter(
            BlocklyAssignment.id == assignment_id
        ).first()

        if not original:
            raise ValueError(f"Exercice {assignment_id} introuvable")

        prompt = f"""Voici un exercice que tu as généré :
Titre : {original.title}
Description : {original.description}

L'enseignant demande de le modifier :
"{feedback}"

Génère une version améliorée sur le même thème et niveau.
Retourne uniquement le JSON, sans aucun autre texte."""

        raw           = self._call_ollama(prompt)
        exercise_data = self._parse_response(raw)
        self._validate(exercise_data)

        original.title             = exercise_data["title"]
        original.description       = exercise_data["description"]
        original.generation_prompt = prompt
        original.updated_at        = datetime.utcnow()
        original.is_published      = False

        original.set_allowed_blocks(exercise_data.get("allowed_blocks"))
        original.set_test_cases(exercise_data["test_cases"])
        original.set_hints(exercise_data.get("hints", []))

        self.db.commit()
        self.db.refresh(original)
        return original

    # ── Publier ───────────────────────────────────────────────────────────────

    def publish(self, assignment_id: str, teacher_id: str) -> BlocklyAssignment:
        """Rend l'exercice visible aux étudiants."""
        assignment = self.db.query(BlocklyAssignment).filter(
            BlocklyAssignment.id == assignment_id,
            BlocklyAssignment.is_active == True,
        ).first()

        if not assignment:
            raise ValueError(f"Exercice {assignment_id} introuvable")

        assignment.is_published = True
        assignment.updated_at   = datetime.utcnow()
        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    # ── Lister ────────────────────────────────────────────────────────────────

    def list_assignments(
        self,
        course_id: str | None = None,
        published_only: bool = True,
        limit: int = 50,
    ) -> list[BlocklyAssignment]:

        query = self.db.query(BlocklyAssignment).filter(
            BlocklyAssignment.is_active == True
        )
        if course_id:
            query = query.filter(BlocklyAssignment.course_id == course_id)
        if published_only:
            query = query.filter(BlocklyAssignment.is_published == True)

        return (
            query.order_by(BlocklyAssignment.created_at.desc()).limit(limit).all()
        )

    # ── Méthodes privées ──────────────────────────────────────────────────────

    def _build_prompt(
        self,
        theme: str,
        level: str,
        objective: str,
        num_test_cases: int,
        allowed_blocks_hint: list[str] | None = None,
    ) -> str:
        prompt = (
            f"Génère un exercice Blockly :\n"
            f"- Thème : {theme}\n"
            f"- Niveau : {level}\n"
            f"- Objectif : {objective}\n"
            f"- Nombre de cas de test : {num_test_cases}"
        )
        if allowed_blocks_hint:
            prompt += f"\n- Blocs suggérés : {', '.join(allowed_blocks_hint)}"
        prompt += "\n\nRetourne uniquement le JSON."
        return prompt

    def _call_ollama(self, user_prompt: str) -> str:
        """
        Appelle Ollama et assemble la réponse complète.
        Même pattern que generate_feedback_stream dans blockly_service.py.
        """
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model"  : OLLAMA_MODEL,
                    "prompt" : f"{SYSTEM_PROMPT}\n\nUtilisateur : {user_prompt}",
                    "stream" : True,
                    "options": {"temperature": 0.7, "num_predict": 1000},
                },
                stream=True,
                timeout=120,
            )
            full_text = ""
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode("utf-8"))
                        if "response" in data:
                            full_text += data["response"]
                        if data.get("done"):
                            break
                    except Exception:
                        continue
            return full_text

        except requests.exceptions.ConnectionError:
            raise ValueError(
                "Ollama n'est pas accessible sur localhost:11434. "
                "Lance-le avec : ollama serve"
            )
        except requests.exceptions.Timeout:
            raise ValueError("Ollama a mis trop de temps à répondre (timeout 120s).")

    def _parse_response(self, raw: str) -> dict:
        """
        Parse le JSON retourné par Ollama.
        Robuste : cherche le premier { et le dernier } même
        si le modèle a ajouté du texte autour.
        """
        text = raw.strip()

        # Extraire le JSON même s'il y a du texte autour
        start = text.find("{")
        end   = text.rfind("}")

        if start == -1 or end == -1 or start >= end:
            logger.error(f"Pas de JSON dans la réponse : {text[:300]}")
            raise ValueError(
                "Le modèle n'a pas retourné de JSON valide. "
                "Essaie de regénérer."
            )

        json_text = text[start : end + 1]

        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON invalide : {json_text[:300]}")
            raise ValueError(f"JSON invalide retourné par Ollama : {e}")

    def _validate(self, data: dict) -> None:
        """Vérifie que toutes les données nécessaires sont présentes."""

        for field in ["title", "description", "test_cases"]:
            if field not in data:
                raise ValueError(f"Champ manquant dans la réponse IA : '{field}'")

        if not data["title"].strip():
            raise ValueError("Le titre généré est vide.")

        if not data.get("test_cases"):
            raise ValueError("Aucun cas de test généré.")

        for i, tc in enumerate(data["test_cases"]):
            if "expected_output" not in tc:
                raise ValueError(f"Cas de test #{i+1} sans 'expected_output'.")

        # Filtrer les blocs invalides sans bloquer
        if data.get("allowed_blocks"):
            invalid = [b for b in data["allowed_blocks"] if b not in VALID_BLOCKLY_BLOCKS]
            if invalid:
                logger.warning(f"Blocs invalides filtrés : {invalid}")
                data["allowed_blocks"] = [
                    b for b in data["allowed_blocks"] if b in VALID_BLOCKLY_BLOCKS
                ]

        # Normaliser le niveau
        if data.get("difficulty") not in ["débutant", "intermédiaire", "avancé"]:
            data["difficulty"] = "débutant"

    def _save_to_db(
        self,
        exercise_data: dict,
        teacher_id: str,
        course_id: str | None,
        generation_prompt: str,
    ) -> BlocklyAssignment:
        """Crée et persiste le BlocklyAssignment."""

        assignment = BlocklyAssignment(
            title             = exercise_data["title"],
            description       = exercise_data["description"],
            difficulty        = exercise_data.get("difficulty", "débutant"),
            max_score         = 100,
            course_id         = course_id,
            generated_by_ai   = True,
            generation_prompt = generation_prompt,
            ai_model_used     = OLLAMA_MODEL,
            created_by        = teacher_id,
            is_published      = False,
            is_active         = True,
        )

        assignment.set_allowed_blocks(exercise_data.get("allowed_blocks"))
        assignment.set_test_cases(exercise_data["test_cases"])
        assignment.set_hints(exercise_data.get("hints", []))

        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)
        return assignment