# backend/open_tutorai/routers/blockly.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json

from open_tutorai.models.database import get_db
from open_tutorai.schemas.blockly import (
    BlocklySubmitRequest,
    BlocklyTestRequest,
    BlocklyTestResponse,
    BlocklySaveWorkspaceRequest,
    BlocklyAssignmentResponse,
    BlocklySubmissionResponse,
     BlocklyGenerateRequest,
    BlocklyGenerateResponse,
    BlocklyRegenerateRequest,
)
from open_tutorai.services.blockly_generator_service import BlocklyGeneratorService
from open_tutorai.services.blockly_service import BlocklyService
from open_webui.utils.auth import get_verified_user

router = APIRouter(prefix="/api/blockly", tags=["Blockly"])


@router.get("/assignment/{assignment_id}", response_model=BlocklyAssignmentResponse)
async def get_blockly_assignment(
    assignment_id: str,
    current_user = Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    service = BlocklyService(db)
    assignment = service.get_assignment(assignment_id, current_user.id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Exercice Blockly introuvable")
    return assignment


@router.post("/test", response_model=BlocklyTestResponse)
async def test_blockly_code(
    payload: BlocklyTestRequest,
    current_user = Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    service = BlocklyService(db)
    result = await service.test_code(
        python_code=payload.python_code,
        assignment_id=payload.assignment_id,
        student_id=current_user.id,
    )
    return result


@router.post("/submit")
async def submit_blockly_exercise(
    payload: BlocklySubmitRequest,
    current_user = Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    service = BlocklyService(db)
    assignment = service.get_assignment(payload.assignment_id, current_user.id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Exercice introuvable")

    # Pré-calculer tout avant le streaming
    execution_result = await service.execute_code(payload.python_code)
    test_results = await service.run_test_cases(
        payload.python_code, assignment["test_cases"]
    )
    score = service.calculate_score(test_results, assignment["max_score"])

    # Sauvegarder avant le streaming
    try:
        submission_id = service.save_submission(
            student_id=current_user.id,
            assignment_id=payload.assignment_id,
            blocks_json=payload.blocks_json,
            python_code=payload.python_code,
            execution_result=execution_result,
            test_results=test_results,
            score=score,
        )
    except Exception:
        submission_id = "temp"

    async def event_stream():
        try:
            # 1. Envoyer le score
            yield f"data: {json.dumps({'type': 'score', 'value': score})}\n\n"

            # 2. Streamer le feedback IA
            async for feedback_chunk in service.generate_feedback_stream(
                python_code=payload.python_code,
                execution_result=execution_result,
                test_results=test_results,
                score=score,
                assignment=assignment,
                student_level="débutant",
            ):
                yield f"data: {json.dumps({'type': 'feedback', 'content': feedback_chunk})}\n\n"

            # 3. Signal de fin
            yield f"data: {json.dumps({'type': 'done', 'submission_id': str(submission_id)})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/history/{student_id}", response_model=list[BlocklySubmissionResponse])
async def get_submission_history(
    student_id: str,
    assignment_id: str | None = None,
    limit: int = 20,
    current_user = Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    if current_user.id != student_id and current_user.role not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    service = BlocklyService(db)
    return service.get_history(
        student_id=student_id,
        assignment_id=assignment_id,
        limit=limit
    )


@router.post("/workspace/save")
async def save_workspace(
    payload: BlocklySaveWorkspaceRequest,
    current_user = Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    service = BlocklyService(db)
    service.save_workspace_draft(
        student_id=current_user.id,
        assignment_id=payload.assignment_id,
        blocks_json=payload.blocks_json,
    )
    return {"status": "saved"}


@router.get("/workspace/{assignment_id}")
async def load_workspace(
    assignment_id: str,
    current_user = Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    service = BlocklyService(db)
    draft = service.get_workspace_draft(
        student_id=current_user.id,
        assignment_id=assignment_id,
    )
    if not draft:
        raise HTTPException(status_code=404, detail="Aucun brouillon trouvé")
    return draft
# ── Endpoint 1 : Générer un exercice ─────────────────────────────────────────
 
@router.post("/generate", response_model=BlocklyGenerateResponse)
async def generate_blockly_assignment(
    payload: BlocklyGenerateRequest,
    current_user=Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    """
    L'enseignant remplit un formulaire (thème + niveau + objectif)
    et l'IA génère un exercice complet sauvegardé en DB.
 
    Réservé aux rôles teacher et admin.
    L'exercice est créé en mode brouillon (is_published=False).
    L'enseignant doit ensuite appeler /publish pour le rendre visible.
    """
    # Seuls les enseignants et admins peuvent générer des exercices
    if current_user.role not in ("teacher", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Seuls les enseignants peuvent générer des exercices",
        )
 
    generator = BlocklyGeneratorService(db)
 
    try:
        assignment = await generator.generate_and_save(
            theme=payload.theme,
            level=payload.level,
            objective=payload.objective,
            teacher_id=current_user.id,
            course_id=payload.course_id,
            num_test_cases=payload.num_test_cases,
            allowed_blocks_hint=payload.allowed_blocks_hint,
        )
    except ValueError as e:
        # L'IA a retourné quelque chose d'invalide
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        # Erreur inattendue (LLM indisponible, timeout, etc.)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la génération : {str(e)}",
        )
 
    # Convertir le modèle DB en réponse API
    data = assignment.to_dict()
    return BlocklyGenerateResponse(**data)
 
 
# ── Endpoint 2 : Générer en streaming ────────────────────────────────────────
 
@router.post("/generate/stream")
async def generate_blockly_assignment_stream(
    payload: BlocklyGenerateRequest,
    current_user=Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    """
    Même chose que /generate mais en streaming SSE.
    L'enseignant voit le JSON apparaître mot par mot dans l'interface,
    comme le feedback IA existant.
 
    Événements SSE envoyés :
      {"type": "chunk",  "content": "..."}   ← morceau du JSON en cours
      {"type": "done",   "assignment_id": "..."} ← exercice sauvegardé
      {"type": "error",  "message": "..."}   ← si ça plante
    """
    if current_user.role not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="Accès non autorisé")
 
    generator = BlocklyGeneratorService(db)
 
    async def event_stream():
        # Accumuler tous les chunks pour sauvegarder à la fin
        full_response = ""
 
        try:
            # 1. Streamer la génération token par token
            async for chunk in generator.generate_stream(
                theme=payload.theme,
                level=payload.level,
                objective=payload.objective,
                num_test_cases=payload.num_test_cases,
            ):
                full_response += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
 
            # 2. Une fois le streaming terminé, sauvegarder en DB
            exercise_data = generator._parse_llm_response(full_response)
            generator._validate_exercise_data(exercise_data)
            assignment = generator._save_to_db(
                exercise_data=exercise_data,
                teacher_id=current_user.id,
                course_id=payload.course_id,
                generation_prompt=payload.objective,
            )
 
            # 3. Signaler la fin avec l'ID de l'exercice créé
            yield f"data: {json.dumps({'type': 'done', 'assignment_id': str(assignment.id)})}\n\n"
 
        except ValueError as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Erreur inattendue : {str(e)}'})}\n\n"
 
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
 
 
# ── Endpoint 3 : Publier un exercice ─────────────────────────────────────────
 
@router.post("/assignment/{assignment_id}/publish")
async def publish_assignment(
    assignment_id: str,
    current_user=Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    """
    Rend un exercice visible aux étudiants.
    L'enseignant clique "Publier" après avoir relu l'exercice généré.
    """
    if current_user.role not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="Accès non autorisé")
 
    generator = BlocklyGeneratorService(db)
 
    try:
        assignment = generator.publish(assignment_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
 
    return {
        "status": "published",
        "assignment_id": assignment.id,
        "title": assignment.title,
    }
 
 
# ── Endpoint 4 : Regénérer avec un commentaire ───────────────────────────────
 
@router.post("/assignment/{assignment_id}/regenerate", response_model=BlocklyGenerateResponse)
async def regenerate_assignment(
    assignment_id: str,
    payload: BlocklyRegenerateRequest,
    current_user=Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    """
    L'enseignant n'est pas satisfait de l'exercice généré.
    Il laisse un commentaire et l'IA produit une version améliorée.
 
    Exemple de feedback : "Les cas de test sont trop simples"
    L'exercice repasse en brouillon (is_published=False) pour relecture.
    """
    if current_user.role not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="Accès non autorisé")
 
    generator = BlocklyGeneratorService(db)
 
    try:
        assignment = await generator.regenerate(
            assignment_id=assignment_id,
            teacher_id=current_user.id,
            feedback=payload.feedback,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la regénération : {str(e)}",
        )
 
    data = assignment.to_dict()
    return BlocklyGenerateResponse(**data)
 
 
# ── Endpoint 5 : Lister les exercices d'un cours ─────────────────────────────
 
@router.get("/assignments")
async def list_assignments(
    course_id: str | None = None,
    current_user=Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    """
    Liste les exercices disponibles.
    - Étudiants : voient seulement les exercices publiés
    - Enseignants/admins : voient aussi les brouillons
    """
    is_teacher = current_user.role in ("teacher", "admin")
 
    generator = BlocklyGeneratorService(db)
    assignments = generator.list_assignments(
        course_id=course_id,
        published_only=not is_teacher,  # étudiants = publiés seulement
    )
 
    return [a.to_dict() for a in assignments]