from fastapi import APIRouter, Request, Body
from app.engine import evaluate
from app.web import render
router=APIRouter()
@router.get('/archive')
def page(request:Request):
    return render(request,'archive')
@router.post('/api/archive')
def calculate(payload:dict=Body(default={})):
    return evaluate(payload,until=7)
