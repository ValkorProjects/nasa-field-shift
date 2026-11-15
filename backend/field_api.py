"""Rota do pacote de dados por talhão (APIRouter próprio; incluído em main.py)."""
from datetime import date

from fastapi import APIRouter, HTTPException

from areas import ScopeError, check_scope
from field_profile import build_field_profile
from geo import GeoError, parse_field
from schemas import FieldProfileRequest

router = APIRouter()


@router.post("/api/field/profile")
def api_field_profile(body: FieldProfileRequest):
    try:
        geom = parse_field(body.field)
        check_scope(geom, body.scope)  # o backend valida o escopo sozinho, sem depender do front (#39)
    except (GeoError, ScopeError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return build_field_profile(geom, date.today(), scope=body.scope)
